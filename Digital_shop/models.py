from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.db.models.signals import post_save
import os
from django.contrib.auth.models import User
from django.utils import timezone



# Create your models here.
class background_slider_images(models.Model):  # Follow naming conventions: class names should be CamelCase
    image = models.ImageField(upload_to='carousel_images/')  # Store images in a specific folder
    order = models.PositiveIntegerField(default=0)  # Order of the carousel items

    class Meta:
        ordering = ['order']  # Order items by the 'order' field
        verbose_name = 'Background Slider Image'
        verbose_name_plural = 'Background Slider Images'

    def __str__(self):
        return f"Slide {self.order}" 



# Utility function to handle file uploads based on product type
def upload_to_based_on_type(instance, filename):
    if instance.product_type == 'book':
        return f'books/{filename}'
    elif instance.product_type == 'video':
        return f'videos/{filename}'
    elif instance.product_type == 'audio':
        return f'audios/{filename}'
    return f'other/{filename}'




class Products(models.Model):
    PRODUCT_TYPES = [
        ('book', 'Book'),
        ('video', 'Video'),
        ('audio', 'Audio'),
    ]
    
    name = models.CharField(max_length=200)
    desc = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price of the product
    product_type = models.CharField(max_length=10, choices=PRODUCT_TYPES)
    product_file = models.FileField(upload_to='uploads/')  # The file to download (e.g., PDF, MP3, MP4)
    image = models.ImageField(upload_to='images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Track users who have purchased the product
    purchased_by = models.ManyToManyField(User, related_name='purchased_products', blank=True)

    # New is_featured column to mark a product as featured
    is_featured = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

        
        
        

# Signal to delete files when the product instance is deleted
@receiver(post_delete, sender=Products)
def delete_files_on_product_delete(sender, instance, **kwargs):
    # Delete product_file if it exists
    if instance.product_file and os.path.isfile(instance.product_file.path):
        os.remove(instance.product_file.path)
    
    # Delete image if it exists
    if instance.image and os.path.isfile(instance.image.path):
        os.remove(instance.image.path)
        
        

class PasswordResetCode(models.Model):
    email = models.EmailField(max_length=254)  # Store the email address associated with the reset code
    reset_code = models.CharField(max_length=64)  # The reset code (should be securely generated)
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp when the code was created
    expires_at = models.DateTimeField()  # Expiration time for the reset code

    def is_expired(self):
        """Check if the reset code is expired."""
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Reset code for {self.email}"        
    
    


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # Ensures one cart per user
    created_at = models.DateTimeField(auto_now_add=True)  # Automatically set the timestamp when created

    def __str__(self):
        return f"Cart for {self.user.username}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='cart_items')
    product = models.ForeignKey(Products, on_delete=models.CASCADE)  # Assuming you have a Products model
    quantity = models.PositiveIntegerField(default=0)

    def get_total_price(self):
        return self.product.price * self.quantity

# Signal to create a cart when a user is created
@receiver(post_save, sender=User)
def create_cart(sender, instance, created, **kwargs):
    if created:
        Cart.objects.create(user=instance)    
        
        
        

class Membership(models.Model):
    COURSE_CHOICES = [
        ('OGS', 'Organization Growth Strategies'),
        ('LS', 'Leadership'),
        ('PM', 'Principles of Ministry'),
    ]

    LEVEL_CHOICES = [
        ('OGS501', 'Level 1 - OGS501'),
        ('OGS502', 'Level 2 - OGS502'),
        ('LS501', 'Level 1 - LS501'),
        ('LS502', 'Level 2 - LS502'),
        ('PM501', 'Level 1 - PM501'),
        ('PM502', 'Level 2 - PM502'),
    ]

    # Basic course info
    course_name = models.CharField(max_length=255, choices=COURSE_CHOICES)
    level_1 = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    level_1_price = models.DecimalField(max_digits=10, decimal_places=2, default=10000.00)  # Price for Level 1
    level_2 = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    level_2_price = models.DecimalField(max_digits=10, decimal_places=2, default=10000.00)  # Price for Level 2
    training_sections = models.IntegerField(default=2)
    # Field for tracking who purchased this membership
    purchased_by = models.ManyToManyField(User, related_name="memberships_purchased", blank=True)

    def __str__(self):
        return f"{self.course_name} - {self.level_1}/{self.level_2}"

    class Meta:
        verbose_name = "Membership"
        verbose_name_plural = "Memberships"
        
        


class UserMembershipLevel(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    membership = models.CharField(max_length=255)  # Store the course name as a CharField
    level = models.CharField(max_length=20)
    training_sections = models.IntegerField(default=3)
    purchased_at = models.DateTimeField(auto_now_add=True)  # Timestamp for when the purchase was made

    class Meta:
        verbose_name = "User Membership Level"
        verbose_name_plural = "User Membership Levels"
        unique_together = ('user', 'membership', 'level', 'training_sections')  # Ensure a user cannot have the same level multiple times for the same membership

    def __str__(self):
        return f"{self.user.username} - {self.membership.course_name} - {self.level}"
