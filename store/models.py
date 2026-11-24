from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    icon = models.CharField(max_length=8, default="🛍️", help_text="Oru emoji")

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, related_name="products", on_delete=models.CASCADE)
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    emoji = models.CharField(max_length=8, blank=True, help_text="Image illana ithu display aagum")
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    old_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock = models.PositiveIntegerField(default=10)
    image_url = models.URLField(max_length=500, blank=True)
    is_featured = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:150] or "product"
            slug, n = base, 2
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("product_detail", args=[self.slug])

    @property
    def symbol(self):
        return self.emoji or self.category.icon

    @property
    def tone(self):
        return (self.pk or 0) % 6

    @property
    def discount_percent(self):
        if self.old_price and self.old_price > self.price:
            return int((self.old_price - self.price) * 100 / self.old_price)
        return 0

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def low_stock(self):
        return 0 < self.stock <= 5

    def __str__(self):
        return self.name


class Review(models.Model):
    product = models.ForeignKey(Product, related_name="reviews", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("product", "user")
        ordering = ["-created"]

    def __str__(self):
        return f"{self.product} - {self.rating}★"


class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="wishlist", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, related_name="wishlisted", on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "product")
        ordering = ["-created"]


class Coupon(models.Model):
    code = models.CharField(max_length=30, unique=True)
    percent = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(90)])
    min_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    active = models.BooleanField(default=True)
    valid_until = models.DateTimeField(null=True, blank=True)

    def validate_for(self, subtotal):
        if not self.active:
            return False, "Intha coupon ippo active illa"
        if self.valid_until and timezone.now() > self.valid_until:
            return False, "Coupon expire aayiduchu"
        if subtotal < self.min_amount:
            return False, f"Minimum ₹{int(self.min_amount)} order venum intha coupon-ku"
        return True, ""

    def __str__(self):
        return f"{self.code} ({self.percent}%)"


class Order(models.Model):
    STATUS_CHOICES = [
        ("placed", "Placed"),
        ("confirmed", "Confirmed"),
        ("shipped", "Shipped"),
        ("out_for_delivery", "Out for delivery"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ]
    PAYMENT_CHOICES = [
        ("cod", "Cash on Delivery"),
        ("upi", "UPI (demo)"),
        ("card", "Card (demo)"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="orders", on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    city = models.CharField(max_length=60)
    pincode = models.CharField(max_length=10)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default="cod")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="placed")
    coupon_code = models.CharField(max_length=30, blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created"]

    @property
    def code(self):
        return f"SZ{self.pk:05d}"

    @property
    def can_cancel(self):
        return self.status in ("placed", "confirmed")

    def restore_stock(self):
        for item in self.items.exclude(product__isnull=True):
            Product.objects.filter(pk=item.product_id).update(stock=F("stock") + item.quantity)

    def __str__(self):
        return self.code


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=150)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def line_total(self):
        return self.price * self.quantity
