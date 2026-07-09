from django import template
from django.utils.safestring import mark_safe
import json

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Récupère une valeur d'un dictionnaire par sa clé.
    Utilisation: {{ my_dict|get_item:key }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter
def get_item_default(dictionary, key, default=0):
    """
    Récupère une valeur d'un dictionnaire par sa clé avec valeur par défaut.
    Utilisation: {{ my_dict|get_item_default:key }}
    """
    if dictionary is None:
        return default
    return dictionary.get(key, default)


@register.filter
def dict_values(dictionary):
    """
    Retourne les valeurs d'un dictionnaire.
    Utilisation: {{ my_dict|dict_values }}
    """
    if dictionary is None:
        return []
    return dictionary.values()


@register.filter
def dict_keys(dictionary):
    """
    Retourne les clés d'un dictionnaire.
    Utilisation: {{ my_dict|dict_keys }}
    """
    if dictionary is None:
        return []
    return dictionary.keys()


@register.filter
def to_json(value):
    """
    Convertit une valeur en JSON.
    Utilisation: {{ my_dict|to_json }}
    """
    return mark_safe(json.dumps(value))


@register.filter
def multiply(value, arg):
    """
    Multiplie une valeur par un argument.
    Utilisation: {{ value|multiply:arg }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def divide(value, arg):
    """
    Divise une valeur par un argument.
    Utilisation: {{ value|divide:arg }}
    """
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def percentage(value, total):
    """
    Calcule un pourcentage.
    Utilisation: {{ value|percentage:total }}
    """
    try:
        if float(total) == 0:
            return 0
        return round((float(value) / float(total)) * 100, 1)
    except (ValueError, TypeError):
        return 0


@register.filter
def format_timedelta(seconds):
    """
    Formate un nombre de secondes en HH:MM:SS.
    Utilisation: {{ seconds|format_timedelta }}
    """
    try:
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}min"
        elif minutes > 0:
            return f"{minutes}min {secs}s"
        else:
            return f"{secs}s"
    except (ValueError, TypeError):
        return "0s"


@register.filter
def truncate_words(value, num_words):
    """
    Tronque un texte au nombre de mots spécifié.
    Utilisation: {{ text|truncate_words:20 }}
    """
    try:
        words = value.split()
        if len(words) <= num_words:
            return value
        return ' '.join(words[:num_words]) + '...'
    except (ValueError, TypeError, AttributeError):
        return value


@register.filter
def get_class_name(obj):
    """
    Retourne le nom de la classe d'un objet.
    Utilisation: {{ object|get_class_name }}
    """
    if obj is None:
        return ''
    return obj.__class__.__name__


@register.simple_tag
def active_class(request, urls, active_class='active'):
    """
    Retourne 'active' si l'URL courante correspond à l'une des URLs passées.
    Utilisation: {% active_class request 'dashboard' 'unites_list' %}
    """
    import re
    if request is None:
        return ''
    
    current_path = request.path
    
    for url_name in urls.split(','):
        url_name = url_name.strip()
        if url_name in current_path:
            return active_class
    return ''


@register.simple_tag
def define(val=None):
    """
    Définit une variable temporaire.
    Utilisation: {% define "ma_valeur" as ma_variable %}
    """
    return val


@register.filter
def has_group(user, group_name):
    """
    Vérifie si un utilisateur appartient à un groupe.
    Utilisation: {{ user|has_group:"Enseignants" }}
    """
    if user is None:
        return False
    return user.groups.filter(name=group_name).exists()


@register.filter
def get_verbose_name(obj, field_name):
    """
    Récupère le verbose_name d'un champ.
    Utilisation: {{ object|get_verbose_name:"title" }}
    """
    if obj is None:
        return field_name
    try:
        return obj._meta.get_field(field_name).verbose_name
    except:
        return field_name


@register.filter
def get_help_text(obj, field_name):
    """
    Récupère le help_text d'un champ.
    Utilisation: {{ object|get_help_text:"title" }}
    """
    if obj is None:
        return ''
    try:
        return obj._meta.get_field(field_name).help_text
    except:
        return ''
    
    