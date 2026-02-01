from decimal import Decimal

from django import template

register = template.Library()


@register.filter
def brl(value):
    if value is None:
        return "0,00"
    try:
        number = Decimal(value)
    except Exception:
        return value
    formatted = f"{number:,.2f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


@register.filter
def get_item(dictionary, key):
    """
    Template filter to access dictionary items by key.
    Usage: {{ mydict|get_item:key_variable }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)
