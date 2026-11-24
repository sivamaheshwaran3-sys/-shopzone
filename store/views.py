from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Avg, Count, DecimalField, F, Q, Sum
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .cart import Cart
from .forms import CheckoutForm, ProductForm, RegisterForm
from .models import Category, Coupon, Order, OrderItem, Product, Review, Wishlist

staff_required = user_passes_test(lambda u: u.is_active and u.is_staff, login_url="login")


# ---------------------------------------------------------------- helpers
def is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def with_ratings(qs):
    return qs.annotate(rating_avg=Avg("reviews__rating"), rating_count=Count("reviews", distinct=True))


def safe_next(request, default):
    nxt = request.POST.get("next") or request.GET.get("next")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return nxt
    return default


def active_products():
    return with_ratings(Product.objects.filter(active=True).select_related("category"))


# ---------------------------------------------------------------- storefront
def home(request):
    base = active_products()
    ctx = {
        "featured": base.filter(is_featured=True).order_by("-created")[:8],
        "latest": base.order_by("-created")[:8],
        "deals": base.filter(old_price__gt=F("price")).order_by("-created")[:4],
        "total_products": Product.objects.filter(active=True).count(),
    }
    return render(request, "store/home.html", ctx)


def product_list(request):
    q = request.GET.get("q", "").strip()
    cat = request.GET.get("category", "")
    sort = request.GET.get("sort", "new")
    qs = active_products()

    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(category__name__icontains=q))
    if cat:
        qs = qs.filter(category__slug=cat)
    for key, lookup in (("min_price", "price__gte"), ("max_price", "price__lte")):
        raw = request.GET.get(key, "").strip()
        if raw:
            try:
                qs = qs.filter(**{lookup: Decimal(raw)})
            except InvalidOperation:
                pass
    if request.GET.get("in_stock"):
        qs = qs.filter(stock__gt=0)
    if request.GET.get("deals"):
        qs = qs.filter(old_price__gt=F("price"))

    if sort == "rating":
        qs = qs.order_by(F("rating_avg").desc(nulls_last=True), "-created")
    else:
        qs = qs.order_by({"price_low": "price", "price_high": "-price", "name": "name"}.get(sort, "-created"))

    page_obj = Paginator(qs, 9).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "store/product_list.html", {
        "page_obj": page_obj,
        "q": q,
        "active_cat": cat,
        "sort": sort,
        "querystring": params.urlencode(),
        "result_count": page_obj.paginator.count,
    })


def product_detail(request, slug):
    product = get_object_or_404(with_ratings(Product.objects.select_related("category")), slug=slug, active=True)

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login')}?next={request.path}")
        try:
            rating = int(request.POST.get("rating", 0))
        except ValueError:
            rating = 0
        if rating not in range(1, 6):
            messages.error(request, "Star rating select pannunga")
        else:
            Review.objects.update_or_create(
                product=product, user=request.user,
                defaults={"rating": rating, "comment": request.POST.get("comment", "").strip()[:1000]},
            )
            messages.success(request, "Review save aayiduchu. Nandri! ⭐")
        return redirect(product)

    buyers = set(
        OrderItem.objects.filter(product=product).exclude(order__status="cancelled")
        .values_list("order__user_id", flat=True)
    )
    reviews = list(product.reviews.select_related("user"))
    for r in reviews:
        r.verified = r.user_id in buyers
    counts = {r["rating"]: r["c"] for r in product.reviews.values("rating").annotate(c=Count("id"))}
    total = sum(counts.values())
    distribution = [
        {"star": s, "count": counts.get(s, 0), "pct": int(counts.get(s, 0) * 100 / total) if total else 0}
        for s in range(5, 0, -1)
    ]

    related = active_products().filter(category=product.category).exclude(pk=product.pk).order_by("-created")[:4]

    recent_ids = [i for i in request.session.get("recent", []) if i != product.id]
    recent = sorted(active_products().filter(id__in=recent_ids), key=lambda p: recent_ids.index(p.id))[:4]
    request.session["recent"] = ([product.id] + recent_ids)[:7]

    return render(request, "store/product_detail.html", {
        "product": product,
        "reviews": reviews,
        "distribution": distribution,
        "related": related,
        "recent": recent,
        "my_review": next((r for r in reviews if r.user_id == request.user.id), None),
        "rating_choices": [5, 4, 3, 2, 1],
    })


# ---------------------------------------------------------------- cart
def cart_view(request):
    cart = Cart(request)
    return render(request, "store/cart.html", {"items": cart.items(), "t": cart.totals()})


@require_POST
def cart_add(request, pk):
    product = get_object_or_404(Product, pk=pk, active=True)
    try:
        qty = max(1, int(request.POST.get("quantity", 1)))
    except ValueError:
        qty = 1
    cart = Cart(request)
    current = cart.data.get(str(pk), 0)
    ok, msg = True, f"'{product.name}' cart-la add aayiduchu 🛒"

    if product.stock <= 0:
        ok, msg = False, "Sorry, intha product stock-la illa"
    elif current + qty > product.stock:
        cart.set(pk, product.stock)
        msg = f"Stock {product.stock} mattum thaan irukku — cart-la athe vachirukkom"
    else:
        cart.add(pk, qty)

    if is_ajax(request):
        return JsonResponse({"ok": ok, "message": msg, "count": cart.count()}, status=200 if ok else 400)
    (messages.success if ok else messages.error)(request, msg)
    if ok and request.POST.get("buy_now"):
        return redirect("checkout")
    return redirect(safe_next(request, "cart"))


@require_POST
def cart_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    try:
        qty = int(request.POST.get("quantity", 1))
    except ValueError:
        qty = 1
    if qty > product.stock:
        qty = product.stock
        messages.info(request, f"Max {product.stock} mattum available")
    Cart(request).set(pk, qty)
    return redirect("cart")


@require_POST
def cart_remove(request, pk):
    Cart(request).remove(pk)
    messages.info(request, "Item remove pannitom")
    return redirect("cart")


@require_POST
def apply_coupon(request):
    code = request.POST.get("code", "").strip()
    cart = Cart(request)
    coupon = Coupon.objects.filter(code__iexact=code).first()
    subtotal = cart.totals()["subtotal"]
    if not coupon:
        messages.error(request, "Invalid coupon code")
    else:
        ok, msg = ok, msg = coupon.validate_for(subtotal)
        if ok:
            request.session["coupon"] = coupon.code
            messages.success(request, f"🎉 {coupon.code} apply aayiduchu — {coupon.percent}% off!")
        else:
            messages.error(request, msg)
    return redirect("cart")


@require_POST
def remove_coupon(request):
    request.session.pop("coupon", None)
    messages.info(request, "Coupon remove pannitom")
    return redirect("cart")


# ---------------------------------------------------------------- checkout & orders
class StockError(Exception):
    pass


@transaction.atomic
def place_order(user, data, cart):
    products = {
        p.id: p for p in Product.objects.select_for_update().filter(id__in=[int(i) for i in cart.data], active=True)
    }
    lines = []
    for pid, qty in cart.data.items():
        p = products.get(int(pid))
        if p is None:
            continue
        if p.stock < qty:
            raise StockError(f"'{p.name}' — {p.stock} mattum thaan irukku")
        lines.append((p, qty))
    if not lines:
        raise StockError("Cart empty-ah irukku")

    t = cart.totals()
    order = Order.objects.create(
        user=user, **data,
        coupon_code=t["coupon"].code if t["coupon"] else "",
        subtotal=t["subtotal"], discount=t["discount"], shipping=t["shipping"], total=t["total"],
    )
    for p, qty in lines:
        OrderItem.objects.create(order=order, product=p, name=p.name, price=p.price, quantity=qty)
        p.stock -= qty
        p.save(update_fields=["stock"])
    return order


@login_required
def checkout(request):
    cart = Cart(request)
    if not cart.items():
        messages.info(request, "Mudhalla cart-la products add pannunga")
        return redirect("shop")

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                order = place_order(request.user, form.cleaned_data, cart)
            except StockError as e:
                messages.error(request, str(e))
                return redirect("cart")
            cart.clear()
            return redirect("order_success", pk=order.pk)
    else:
        last = request.user.orders.first()
        initial = {"full_name": request.user.get_full_name()}
        if last:
            initial.update(full_name=last.full_name, phone=last.phone, address=last.address,
                           city=last.city, pincode=last.pincode)
        form = CheckoutForm(initial=initial)
    return render(request, "store/checkout.html", {"form": form, "items": cart.items(), "t": cart.totals()})


@login_required
def order_success(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(request, "store/order_success.html", {"order": order})


@login_required
def my_orders(request):
    orders = request.user.orders.prefetch_related("items")
    return render(request, "store/my_orders.html", {"orders": orders})


TIMELINE = [
    ("placed", "Order placed", "📝"),
    ("confirmed", "Confirmed", "✅"),
    ("shipped", "Shipped", "📦"),
    ("out_for_delivery", "Out for delivery", "🚚"),
    ("delivered", "Delivered", "🎉"),
]


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related("items"), pk=pk)
    if order.user_id != request.user.id and not request.user.is_staff:
        raise Http404
    keys = [k for k, _, _ in TIMELINE]
    idx = keys.index(order.status) if order.status in keys else -1
    steps = [
        {"label": label, "icon": icon, "done": i <= idx, "current": i == idx}
        for i, (_, label, icon) in enumerate(TIMELINE)
    ]
    return render(request, "store/order_detail.html", {"order": order, "steps": steps})


@require_POST
@login_required
def cancel_order(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    if order.can_cancel:
        with transaction.atomic():
            order.restore_stock()
            order.status = "cancelled"
            order.save(update_fields=["status", "updated"])
        messages.success(request, f"Order {order.code} cancel aayiduchu")
    else:
        messages.error(request, "Intha order-a ippo cancel panna mudiyathu")
    return redirect("order_detail", pk=pk)


# ---------------------------------------------------------------- wishlist
@login_required
def wishlist_view(request):
    products = with_ratings(
        Product.objects.filter(wishlisted__user=request.user, active=True).select_related("category")
    ).order_by("-wishlisted__created")
    return render(request, "store/wishlist.html", {"products": products})


@require_POST
def wishlist_toggle(request, pk):
    if not request.user.is_authenticated:
        return JsonResponse({"login": f"{reverse('login')}?next={request.POST.get('next', '/')}"}, status=401)
    product = get_object_or_404(Product, pk=pk)
    obj, created = Wishlist.objects.get_or_create(user=request.user, product=product)
    if not created:
        obj.delete()
    return JsonResponse({
        "added": created,
        "count": Wishlist.objects.filter(user=request.user).count(),
        "message": "Wishlist-la add aayiduchu ❤️" if created else "Wishlist-la irundhu remove pannitom",
    })


# ---------------------------------------------------------------- auth
def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f"Welcome {user.first_name}! 🎉")
        return redirect(safe_next(request, "home"))
    return render(request, "auth/register.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, "Logout aayiduchu. Meendum vaanga! 👋")
    return redirect("home")


# ---------------------------------------------------------------- admin dashboard (staff only)
@staff_required
def dashboard(request):
    valid = Order.objects.exclude(status="cancelled")
    today = timezone.localdate()
    start = today - timedelta(days=6)
    start_dt = timezone.make_aware(datetime.combine(start, time.min))

    daily = defaultdict(Decimal)
    for created, total in valid.filter(created__gte=start_dt).values_list("created", "total"):
        daily[timezone.localtime(created).date()] += total
    chart = [{"label": (start + timedelta(days=i)).strftime("%a"), "value": daily[start + timedelta(days=i)]}
             for i in range(7)]
    peak = max([c["value"] for c in chart] + [Decimal("1")])
    for c in chart:
        c["pct"] = max(int(c["value"] * 100 / peak), 4 if c["value"] else 2)

    labels = dict(Order.STATUS_CHOICES)
    status_counts = [
        {"key": r["status"], "label": labels.get(r["status"], r["status"]), "n": r["n"]}
        for r in Order.objects.values("status").annotate(n=Count("id")).order_by("-n")
    ]
    top = (OrderItem.objects.exclude(order__status="cancelled").values("name")
           .annotate(qty=Sum("quantity"), rev=Sum(F("price") * F("quantity"), output_field=DecimalField()))
           .order_by("-qty")[:5])

    from django.contrib.auth.models import User
    return render(request, "dashboard/dashboard.html", {
        "revenue": valid.aggregate(s=Sum("total"))["s"] or 0,
        "orders_count": Order.objects.count(),
        "pending": Order.objects.filter(status__in=["placed", "confirmed"]).count(),
        "products_count": Product.objects.count(),
        "users_count": User.objects.filter(is_staff=False).count(),
        "chart": chart,
        "week_total": sum(daily.values(), Decimal("0")),
        "status_counts": status_counts,
        "top_products": top,
        "low_stock": Product.objects.filter(stock__lte=5, active=True).order_by("stock")[:6],
        "recent_orders": Order.objects.select_related("user")[:6],
        "tab": "overview",
    })


@staff_required
def manage_products(request):
    q = request.GET.get("q", "").strip()
    qs = Product.objects.select_related("category").order_by("-created")
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(category__name__icontains=q))
    page_obj = Paginator(qs, 12).get_page(request.GET.get("page"))
    return render(request, "dashboard/manage_products.html", {"page_obj": page_obj, "q": q, "tab": "products"})


@staff_required
def product_form(request, pk=None):
    instance = get_object_or_404(Product, pk=pk) if pk else None
    form = ProductForm(request.POST or None, instance=instance)
    if request.method == "POST" and form.is_valid():
        p = form.save()
        messages.success(request, f"'{p.name}' save aayiduchu ✅")
        return redirect("manage_products")
    return render(request, "dashboard/product_form.html", {"form": form, "product": instance, "tab": "products"})


@require_POST
@staff_required
def product_delete(request, pk):
    p = get_object_or_404(Product, pk=pk)
    name = p.name
    p.delete()
    messages.success(request, f"'{name}' delete aayiduchu")
    return redirect("manage_products")


@staff_required
def manage_orders(request):
    status = request.GET.get("status", "")
    q = request.GET.get("q", "").strip()
    qs = Order.objects.select_related("user").order_by("-created")
    if status:
        qs = qs.filter(status=status)
    if q:
        digits = q.upper().replace("SZ", "")
        qs = qs.filter(Q(full_name__icontains=q) | Q(user__username__icontains=q) | Q(pk=int(digits) if digits.isdigit() else -1))
    page_obj = Paginator(qs, 15).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "dashboard/manage_orders.html", {
        "page_obj": page_obj, "status": status, "q": q, "statuses": Order.STATUS_CHOICES,
        "querystring": params.urlencode(), "tab": "orders",
    })


@require_POST
@staff_required
def update_order_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    new = request.POST.get("status")
    valid = dict(Order.STATUS_CHOICES)
    if new not in valid:
        messages.error(request, "Invalid status")
    elif order.status == "cancelled":
        messages.error(request, "Cancel aana order-a maathha mudiyathu")
    elif new != order.status:
        with transaction.atomic():
            if new == "cancelled":
                order.restore_stock()
            order.status = new
            order.save(update_fields=["status", "updated"])
        messages.success(request, f"{order.code} → {valid[new]}")
    return redirect(safe_next(request, "manage_orders"))


# ---------------------------------------------------------------- JSON APIs
def product_json(request, p):
    return {
        "id": p.id,
        "name": p.name,
        "slug": p.slug,
        "category": p.category.name,
        "price": float(p.price),
        "old_price": float(p.old_price) if p.old_price else None,
        "discount_percent": p.discount_percent,
        "stock": p.stock,
        "image": p.image_url,
        "emoji": p.symbol,
        "rating": round(p.rating_avg or 0, 1),
        "reviews": p.rating_count,
        "url": request.build_absolute_uri(p.get_absolute_url()),
    }


def api_products(request):
    qs = active_products()
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if request.GET.get("category"):
        qs = qs.filter(category__slug=request.GET["category"])
    qs = qs.order_by({"price_low": "price", "price_high": "-price"}.get(request.GET.get("sort"), "-created"))
    page = Paginator(qs, 12).get_page(request.GET.get("page"))
    return JsonResponse({
        "count": page.paginator.count,
        "page": page.number,
        "pages": page.paginator.num_pages,
        "results": [product_json(request, p) for p in page],
    })


def api_search(request):
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"results": []})
    qs = Product.objects.filter(active=True).filter(Q(name__icontains=q) | Q(category__name__icontains=q))
    results = [
        {"name": p.name, "price": float(p.price), "image": p.image_url, "emoji": p.symbol,
         "category": p.category.name, "url": p.get_absolute_url()}
        for p in qs.select_related("category")[:6]
    ]
    return JsonResponse({"results": results})


@login_required
def api_orders(request):
    qs = Order.objects.prefetch_related("items")
    if not request.user.is_staff:
        qs = qs.filter(user=request.user)
    data = [
        {
            "id": o.id, "code": o.code, "status": o.status, "total": float(o.total),
            "payment": o.get_payment_method_display(), "created": o.created.isoformat(),
            "items": [{"name": i.name, "price": float(i.price), "quantity": i.quantity} for i in o.items.all()],
        }
        for o in qs[:50]
    ]
    return JsonResponse({"count": len(data), "results": data})
