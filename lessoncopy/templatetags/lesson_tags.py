from django import template
from django.utils.safestring import mark_safe
import json

register = template.Library()

@register.filter
def render_content(value):
    """Convert structured content into HTML."""
    if not value:
        return ""
    if isinstance(value, str):
        # backward compatibility for old text content
        return mark_safe(f'<div class="old-content">{value}</div>')

    html = []
    if value.get('type') == 'section':
        for child in value.get('children', []):
            html.append(render_block(child))
    return mark_safe('\n'.join(html))

def render_block(block):
    t = block.get('type')
    if t == 'paragraph':
        return f'<p class="lesson-paragraph">{block["text"]}</p>'
    elif t == 'bullet':
        level = block.get('level', 0)
        # apply indentation via CSS class
        return f'<div class="bullet-level-{level} bullet-item">• {block["text"]}</div>'
    # add more types as needed (headings, etc.)
    return ''