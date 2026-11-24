from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "ShopZone Admin"
admin.site.site_title = "ShopZone"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("store.urls")),
]
