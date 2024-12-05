from .models import Membership

def has_purchased_membership(request):
    """Add a variable to check if the user has purchased any memberships."""
    if request.user.is_authenticated:
        return {
            "has_purchased_membership": Membership.objects.filter(purchased_by=request.user).exists()
        }
    return {"has_purchased_membership": False}
