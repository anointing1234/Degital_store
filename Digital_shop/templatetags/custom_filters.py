from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply the value by the arg."""
    try:
        return value * arg
    except (ValueError, TypeError):
        return 0  # Return 0 if there's an error
    
    



@register.filter
def filter_by_type(products, product_type):
    return [product for product in products if getattr(product, 'product_type') == product_type]