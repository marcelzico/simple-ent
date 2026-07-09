# users/templatetags/custom_form_tags.py
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def render_field(field):
    """Custom field rendering without crispy_forms"""
    
    # Add Bootstrap classes to the field
    field_classes = field.field.widget.attrs.get('class', '')
    
    if field.field.widget.__class__.__name__ == 'Select':
        if 'form-select' not in field_classes:
            field.field.widget.attrs['class'] = field_classes + ' form-select'
    elif field.field.widget.__class__.__name__ == 'CheckboxInput':
        if 'form-check-input' not in field_classes:
            field.field.widget.attrs['class'] = field_classes + ' form-check-input'
    elif field.field.widget.__class__.__name__ not in ['CheckboxInput', 'RadioSelect']:
        if 'form-control' not in field_classes:
            field.field.widget.attrs['class'] = field_classes + ' form-control'
    
    # Render the field based on its type
    if field.field.widget.__class__.__name__ == 'CheckboxInput':
        html = f'''
        <div class="form-check mb-3">
            {field}
            <label class="form-check-label" for="{field.id_for_label}">
                {field.label}
            </label>
        '''
        if field.help_text:
            html += f'<small class="form-text text-muted d-block">{field.help_text}</small>'
        if field.errors:
            html += f'<div class="invalid-feedback d-block">{"".join([str(e) for e in field.errors])}</div>'
        html += '</div>'
    else:
        html = f'''
        <div class="form-group mb-3">
            <label for="{field.id_for_label}" class="form-label">
                {field.label}
        '''
        if field.field.required:
            html += '<span class="text-danger"> *</span>'
        html += f'''
            </label>
            {field}
        '''
        if field.help_text:
            html += f'<small class="form-text text-muted">{field.help_text}</small>'
        if field.errors:
            html += f'<div class="invalid-feedback d-block">{"".join([str(e) for e in field.errors])}</div>'
        html += '</div>'
    
    return mark_safe(html)


@register.filter
def add_class(field, css_class):
    """Add CSS class to form field"""
    return field.as_widget(attrs={"class": css_class})


@register.filter
def is_checkbox(field):
    """Check if field is a checkbox"""
    return field.field.widget.__class__.__name__ == 'CheckboxInput'


@register.filter
def is_select(field):
    """Check if field is a select"""
    return field.field.widget.__class__.__name__ == 'Select'