from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from store.models import Category, Coupon, Product

CATEGORIES = [
    ("Electronics", "📱"),
    ("Fashion", "👕"),
    ("Home & Kitchen", "🏠"),
    ("Beauty", "💄"),
    ("Sports", "🏏"),
    ("Books", "📚"),
]

# (category, name, emoji, description, price, old_price, stock, featured)
PRODUCTS = [
    ("Electronics", "Wireless Noise-Cancelling Headphones", "🎧", "40 hour battery, active noise cancellation, deep bass and a super comfortable fit for all-day listening.", 3499, 5999, 25, True),
    ("Electronics", "Smart Watch Pro", "⌚", "AMOLED display, heart-rate and SpO2 tracking, 100+ sports modes and 7 day battery life.", 2799, 4999, 18, True),
    ("Electronics", "Bluetooth Speaker 20W", "🔊", "Waterproof, punchy sound with 12 hour playtime. Perfect for trips and terrace parties.", 1599, 2499, 40, False),
    ("Electronics", "Power Bank 20000mAh", "🔋", "Fast charging, dual output and a slim aluminium body. Charges a phone 4 times.", 1299, 1999, 3, False),
    ("Electronics", "Mechanical Gaming Keyboard", "⌨️", "RGB backlit, hot-swappable blue switches and a sturdy metal frame.", 2199, None, 12, True),
    ("Fashion", "Classic Cotton T-Shirt", "👕", "100% breathable cotton, regular fit, pre-shrunk fabric. Available for everyday wear.", 499, 799, 80, False),
    ("Fashion", "Running Sneakers", "👟", "Lightweight mesh upper with cushioned sole. Built for long runs and daily use.", 1899, 2999, 30, True),
    ("Fashion", "Denim Jacket", "🧥", "Timeless washed denim with a comfortable stretch. Pairs well with anything.", 1799, 2799, 15, False),
    ("Fashion", "Leather Backpack", "🎒", "Water-resistant, laptop sleeve up to 15.6 inch and lots of smart pockets.", 1499, None, 22, False),
    ("Home & Kitchen", "Stainless Steel Water Bottle", "🍶", "1 litre, keeps drinks cold for 24 hours and hot for 12. BPA free.", 599, 899, 60, False),
    ("Home & Kitchen", "Non-stick Cookware Set", "🍳", "5 piece induction-friendly set with cool-touch handles and glass lids.", 2499, 3999, 10, True),
    ("Home & Kitchen", "Ceramic Table Lamp", "💡", "Warm ambient light with a handcrafted ceramic base. Makes any corner cosy.", 999, None, 2, False),
    ("Beauty", "Vitamin C Face Serum", "🧴", "Brightens skin and reduces dark spots. Dermatologically tested, suitable for all skin types.", 449, 699, 50, False),
    ("Beauty", "Aroma Candle Gift Set", "🕯️", "Set of 4 soy wax candles in lavender, vanilla, jasmine and sandalwood.", 699, 999, 35, False),
    ("Sports", "Cricket Bat - English Willow", "🏏", "Grade 2 English willow, perfectly balanced pickup for powerful strokes.", 4299, 5999, 8, True),
    ("Sports", "Yoga Mat 6mm", "🧘", "Extra-thick anti-slip mat with a carry strap. Easy on the joints.", 799, 1299, 45, False),
    ("Books", "Atomic Habits", "📖", "Tiny changes, remarkable results. The world's favourite book on building good habits.", 399, 599, 100, False),
    ("Books", "Python Programming Handbook", "🐍", "Beginner to advanced with 100+ practical examples and mini projects.", 549, 799, 70, True),
]


class Command(BaseCommand):
    help = "Demo categories, products, coupons and users create pannum"

    def handle(self, *args, **options):
        cats = {}
        for name, icon in CATEGORIES:
            cats[name], _ = Category.objects.get_or_create(name=name, defaults={"icon": icon})

        created = 0
        for cat, name, emoji, desc, price, old, stock, featured in PRODUCTS:
            _, was_new = Product.objects.get_or_create(
                name=name,
                defaults=dict(
                    category=cats[cat], emoji=emoji, description=desc, price=Decimal(price),
                    old_price=Decimal(old) if old else None, stock=stock, is_featured=featured,
                ),
            )
            created += was_new

        Coupon.objects.get_or_create(code="WELCOME10", defaults={"percent": 10, "min_amount": 0})
        Coupon.objects.get_or_create(code="SAVE20", defaults={"percent": 20, "min_amount": 2000})
        Coupon.objects.get_or_create(
            code="FESTIVE15",
            defaults={"percent": 15, "min_amount": 1000, "valid_until": timezone.now() + timedelta(days=90)},
        )

        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@shopzone.local", "admin123", first_name="Store Admin")
        if not User.objects.filter(username="demo").exists():
            User.objects.create_user("demo", "demo@shopzone.local", "demo123", first_name="Demo User")

        self.stdout.write(self.style.SUCCESS(f"Done! {created} new products."))
        self.stdout.write("Admin login : admin / admin123")
        self.stdout.write("User login  : demo / demo123")
        self.stdout.write("Coupons     : WELCOME10, SAVE20 (min 2000), FESTIVE15 (min 1000)")
