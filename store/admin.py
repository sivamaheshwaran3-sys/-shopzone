from django.contrib import admin

from .models import Category, Coupon, Order, OrderItem, Product, Review, Wishlist


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "icon", "slug")


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "stock", "is_featured", "active")
    list_filter = ("category", "is_featured", "active")
    search_fields = ("name",)
    list_editable = ("price", "stock", "is_featured", "active")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("code", "user", "total", "status", "created")
    list_filter = ("status", "payment_method")
    inlines = [OrderItemInline]


admin.site.register(Coupon)
admin.site.register(Review)
admin.site.register(Wishlist)
