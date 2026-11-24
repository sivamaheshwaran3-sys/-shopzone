# 🛍️ ShopZone — Django E-Commerce Web Application

Stack: **HTML · CSS · JavaScript · Django · MySQL**

## Features

**Customer side**
- Product catalog with search, live search suggestions, category filter, price range, sort, in-stock / on-sale filters, pagination
- Product page: ratings & reviews (verified-buyer badge), related products, recently viewed
- AJAX add-to-cart, quantity update, remove, **coupon codes**, free-delivery progress bar
- Checkout with address validation, Cash on Delivery / UPI / Card (demo)
- Stock is locked & reduced safely inside a DB transaction
- Order history, **live order-tracking timeline**, cancel order (stock is restored)
- Wishlist (♥), dark mode, fully responsive, toast notifications

**Role-based access**
- **User**: shop, orders, wishlist, reviews
- **Admin** (`is_staff`): custom dashboard — revenue, orders, 7-day sales chart, top products, low-stock alerts,
  product add / edit / delete, order status management (+ Django `/admin/`)

**Backend APIs (JSON)**
- `GET /api/products/?q=&category=&sort=price_low|price_high&page=`
- `GET /api/search/?q=`
- `GET /api/orders/` (login required — users see own orders, admin sees all)

## Setup

```bash
# 1. Virtual env (recommended)
python -m venv venv
venv\Scripts\activate          # Windows      |   source venv/bin/activate  (Mac/Linux)

# 2. Install packages
pip install -r requirements.txt

# 3. Create MySQL database
mysql -u root -p -e "CREATE DATABASE shopzone_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 4. Put your MySQL password in shopzone/settings.py (DATABASES) or set env variables:
#    DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT

# 5. Tables + demo data
python manage.py makemigrations store
python manage.py migrate
python manage.py seed

# 6. Run
python manage.py runserver
```

Open http://127.0.0.1:8000

| Role  | Username | Password |
|-------|----------|----------|
| Admin | `admin`  | `admin123` |
| User  | `demo`   | `demo123` |

Coupons: `WELCOME10` (10%), `SAVE20` (20%, min ₹2000), `FESTIVE15` (15%, min ₹1000)

> MySQL ippo setup panna mudiyala? Quick test: `set USE_SQLITE=1` (Windows) / `export USE_SQLITE=1`
> and run the same commands — SQLite use pannum.

## Project structure

```
shopzone/
├── manage.py
├── requirements.txt
├── shopzone/          settings.py, urls.py
├── store/             models.py, views.py, forms.py, cart.py, urls.py, admin.py
│   └── management/commands/seed.py
├── templates/         base.html, store/, auth/, dashboard/
└── static/            css/style.css, js/main.js
```

## Product images
Seed products use emoji tiles. Admin dashboard → Edit product → paste any **Image URL** to show a real photo.

## Notes
- Payment gateway real-ah connect pannala (demo). Razorpay / Stripe integrate pannalam.
- Production-ku: `DEBUG=0`, strong `SECRET_KEY`, `ALLOWED_HOSTS`, whitenoise / nginx for static files.
