from django import template

register = template.Library()


@register.filter
def whatsapp_format(phone):
    if not phone:
        return ''
    digits = ''.join(c for c in phone if c.isdigit())
    if digits.startswith('0'):
        digits = '254' + digits[1:]
    elif digits.startswith('254'):
        pass
    else:
        digits = '254' + digits
    return digits
