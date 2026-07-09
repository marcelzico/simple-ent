from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    return dictionary.get(key)

@register.filter
def percentage(value, total):
    """Calculate percentage"""
    if total and total > 0:
        return round((value / total) * 100, 1)
    return 0
