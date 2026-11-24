from django.db.models import Count, Q

from .cart import Cart
from .models import Category, Wishlist


def site_globals(request):
    wishlist_ids = set()
    if request.user.is_authenticated:
        wishlist_ids = set(Wishlist.objects.filter(user=request.user).values_list("product_id", flat=True))
    return {
        "cart_count": Cart(request).count(),
        "nav_categories": Category.objects.annotate(n=Count("products", filter=Q(products__active=True))),
        "wishlist_ids": wishlist_ids,
    }
