from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from Digital_shop.models import Cart

class Command(BaseCommand):
    help = 'Create a cart for each existing user'

    def handle(self, *args, **kwargs):
        # Fetch all users
        users = User.objects.all()

        for user in users:
            # Check if the user already has a cart
            if not hasattr(user, 'cart'):
                # Create a new cart for the user
                Cart.objects.create(user=user)
                self.stdout.write(self.style.SUCCESS(f'Created cart for user: {user.username}'))
            else:
                self.stdout.write(self.style.WARNING(f'User {user.username} already has a cart.'))

        self.stdout.write(self.style.SUCCESS('Finished creating carts for all users.'))
