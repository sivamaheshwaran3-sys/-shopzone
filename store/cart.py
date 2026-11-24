from decimal import Decimal

from .models import Coupon, Product

FREE_SHIPPING_ABOVE = Decimal("999")
SHIPPING_FEE = Decimal("49")


class Cart:
    """Session-based cart: {"product_id": quantity}"""

    def __init__(self, request):
        self.session = request.session
        self.data = dict(self.session.get("cart", {}))
        self._items = None

    def _save(self):
        self.session["cart"] = self.data
        self.session.modified = True
        self._items = None

    def count(self):
        return sum(self.data.values())

    def add(self, pid, qty=1):
        key = str(pid)
        self.data[key] = self.data.get(key, 0) + qty
        self._save()

    def set(self, pid, qty):
        if qty <= 0:
            self.remove(pid)
        else:
            self.data[str(pid)] = qty
            self._save()

    def remove(self, pid):
        self.data.pop(str(pid), None)
        self._save()

    def clear(self):
        self.data = {}
        self._save()
        self.session.pop("coupon", None)

    def items(self):
        if self._items is None:
            ids = [int(i) for i in self.data]
            products = Product.objects.filter(id__in=ids, active=True).select_related("category").order_by("id")
            items = []
            for p in products:
                qty = min(self.data.get(str(p.id), 0), p.stock)
                if qty > 0:
                    items.append({"product": p, "quantity": qty, "line_total": p.price * qty})
            self._items = items
        return self._items

    def coupon(self, subtotal):
        code = self.session.get("coupon")
        if not code:
            return None, ""
        c = Coupon.objects.filter(code__iexact=code).first()
        if not c:
            self.session.pop("coupon", None)
            return None, ""
        ok, msg = c.validate_for(subtotal)
        return (c, "") if ok else (None, msg)

    def totals(self):
        items = self.items()
        subtotal = sum((i["line_total"] for i in items), Decimal("0"))
        coupon, coupon_msg = self.coupon(subtotal)
        discount = (subtotal * coupon.percent / 100).quantize(Decimal("1")) if coupon else Decimal("0")
        after = subtotal - discount
        shipping = SHIPPING_FEE if 0 < after < FREE_SHIPPING_ABOVE else Decimal("0")
        return {
            "subtotal": subtotal,
            "discount": discount,
            "shipping": shipping,
            "total": after + shipping,
            "coupon": coupon,
            "coupon_msg": coupon_msg,
            "free_gap": max(FREE_SHIPPING_ABOVE - after, Decimal("0")),
            "free_pct": min(int(after * 100 / FREE_SHIPPING_ABOVE), 100) if after else 0,
        }
