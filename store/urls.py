from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("shop/", views.product_list, name="shop"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),

    path("cart/", views.cart_view, name="cart"),
    path("cart/add/<int:pk>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:pk>/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:pk>/", views.cart_remove, name="cart_remove"),
    path("cart/coupon/", views.apply_coupon, name="apply_coupon"),
    path("cart/coupon/remove/", views.remove_coupon, name="remove_coupon"),

    path("checkout/", views.checkout, name="checkout"),
    path("order/success/<int:pk>/", views.order_success, name="order_success"),
    path("orders/", views.my_orders, name="my_orders"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/cancel/", views.cancel_order, name="cancel_order"),

    path("wishlist/", views.wishlist_view, name="wishlist"),
    path("wishlist/toggle/<int:pk>/", views.wishlist_toggle, name="wishlist_toggle"),

    path("register/", views.register, name="register"),
    path("login/", auth_views.LoginView.as_view(template_name="auth/login.html"), name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Admin dashboard (staff only)
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/products/", views.manage_products, name="manage_products"),
    path("dashboard/products/add/", views.product_form, name="product_add"),
    path("dashboard/products/<int:pk>/edit/", views.product_form, name="product_edit"),
    path("dashboard/products/<int:pk>/delete/", views.product_delete, name="product_delete"),
    path("dashboard/orders/", views.manage_orders, name="manage_orders"),
    path("dashboard/orders/<int:pk>/status/", views.update_order_status, name="update_order_status"),

    # JSON APIs
    path("api/products/", views.api_products, name="api_products"),
    path("api/search/", views.api_search, name="api_search"),
    path("api/orders/", views.api_orders, name="api_orders"),
]
