# users/templatetags/simple_form_tags.py
from django import template

register = template.Library()

@register.simple_tag
def render_form_field(field):
    """Simple form field rendering"""
    html = '<div class="mb-3">'
    
    # Add label
    if field.field.widget.__class__.__name__ != 'CheckboxInput':
        html += f'<label for="{field.id_for_label}" class="form-label">{field.label}</label>'
    
    # Add the field with appropriate classes
    field_classes = 'form-control'
    if field.field.widget.__class__.__name__ == 'Select':
        field_classes = 'form-select'
    elif field.field.widget.__class__.__name__ == 'CheckboxInput':
        field_classes = 'form-check-input'
    
    field.field.widget.attrs['class'] = field_classes
    
    html += str(field)
    
    # Add help text
    if field.help_text:
        html += f'<div class="form-text">{field.help_text}</div>'
    
    # Add errors
    if field.errors:
        html += f'<div class="invalid-feedback d-block">{"".join([str(e) for e in field.errors])}</div>'
    
    html += '</div>'
    
    return html