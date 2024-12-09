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


@register.filter
def get_first_incomplete_course(user_memberships):
    # Sort the memberships by purchase date (oldest first) and filter by incomplete status
    incomplete_courses = [membership for membership in user_memberships if membership.status < 100]
    
    # If there are incomplete courses, return the first one based on the purchase date
    if incomplete_courses:
        incomplete_courses.sort(key=lambda x: x.purchased_at)  # Sort by purchase date (ascending)
        return incomplete_courses[0]  # Return the first incomplete course (oldest)
    
    return None




@register.filter
def dict_get(d, key):
    return d.get(key)