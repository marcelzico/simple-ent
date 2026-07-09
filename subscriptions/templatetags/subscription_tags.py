# subscriptions/templatetags/subscription_tags.py
from django import template

register = template.Library()

@register.filter
def filter_by_status(queryset, status):
    return [item for item in queryset if item.payement_status == status]

@register.filter
def filter_subscriptions_by_status(queryset, status):
    return [item for item in queryset if item.get_subscription_status() == status]

@register.filter
def filter_by_current_status(queryset, status):
    return [item for item in queryset if item.get_subscription_status() == status]

@register.filter
def filter_by_action_type(queryset, action_types):
    types = action_types.split(',')
    return [item for item in queryset if any(t in item.action_type for t in types)]

@register.filter
def multiply(value, arg):
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0