from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def inr(value):
    """1234567 -> ₹12,34,567 (Indian grouping)"""
    try:
        v = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return value
    neg = v < 0
    v = abs(v)
    whole, frac = divmod(v, 1)
    s = str(int(whole))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    if frac:
        s += f".{int(frac * 100):02d}"
    return f"₹{'-' if neg else ''}{s}"


@register.filter
def stars(value):
    try:
        n = round(float(value))
    except (TypeError, ValueError):
        n = 0
    n = max(0, min(5, n))
    return "★" * n + "☆" * (5 - n)
