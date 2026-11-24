import re

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Order, Product


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["full_name", "phone", "address", "city", "pincode", "payment_method"]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
            "payment_method": forms.RadioSelect,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name != "payment_method":
                field.widget.attrs["placeholder"] = field.label

    def clean_phone(self):
        digits = re.sub(r"\D", "", self.cleaned_data["phone"])
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        if len(digits) != 10:
            raise forms.ValidationError("10 digit mobile number kudunga")
        return digits

    def clean_pincode(self):
        pin = self.cleaned_data["pincode"].strip()
        if not re.fullmatch(r"\d{6}", pin):
            raise forms.ValidationError("6 digit pincode kudunga")
        return pin


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "first_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].label = "Full name"
        self.fields["first_name"].required = True
        for f in self.fields.values():
            f.widget.attrs["placeholder"] = f.label
            f.help_text = ""

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Intha email already register aayirukku")
        return email


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "category", "name", "emoji", "description", "price", "old_price",
            "stock", "image_url", "is_featured", "active",
        ]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def clean(self):
        data = super().clean()
        price, old = data.get("price"), data.get("old_price")
        if price is not None and old is not None and old <= price:
            self.add_error("old_price", "Old price, current price-ah vida athigama irukkanum")
        return data
