from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.db.models.signals import post_save
import os
from django.contrib.auth.models import User
from django.utils import timezone
from PIL import Image,UnidentifiedImageError
from io import BytesIO
from django.core.files.base import ContentFile


class background_slider_images(models.Model):  # Follow naming conventions: class names should be CamelCase
    image = models.ImageField(upload_to='carousel_images/')  # Store images in a specific folder
    order = models.PositiveIntegerField(default=0)  # Order of the carousel items

    class Meta:
        ordering = ['order']  # Order items by the 'order' field
        verbose_name = 'Background Slider Image'
        verbose_name_plural = 'Background Slider Images'

    def __str__(self):
        return f"Slide {self.order}"

    def save(self, *args, **kwargs):
        if self.image:
            try:
                # Open the uploaded image
                img = Image.open(self.image)
                img.thumbnail((1920, 1080),Image.Resampling.LANCZOS)  # Resize for large background images
                img = img.convert('RGB')  # Ensure compatibility for WebP
                
                # Convert and save as WebP
                img_io = BytesIO()
                img.save(img_io, format='WEBP', quality=90, method=6)  # High quality WebP
                webp_image_name = os.path.splitext(self.image.name)[0] + '.webp'
                self.image.save(webp_image_name, ContentFile(img_io.getvalue()), save=False)
            except UnidentifiedImageError:
                raise ValueError("The uploaded file is not a valid image.")
        
        super().save(*args, **kwargs)


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
    price = models.DecimalField(max_digits=10, decimal_places=2)
    product_type = models.CharField(max_length=10, choices=PRODUCT_TYPES)
    product_file = models.FileField(upload_to='uploads/')  
    image = models.ImageField(upload_to='images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    purchased_by = models.ManyToManyField(User, related_name='purchased_products', blank=True)
    is_featured = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):
        # Check if an image is uploaded
        if self.image:
            # Open the image using Pillow
            img = Image.open(self.image)
            
            # Resize image for optimization (optional)
            max_size = (800, 800)  # Maximum width and height
            img.thumbnail(max_size,Image.Resampling.LANCZOS)
            
            # Convert to WebP with optimized settings
            img_io = BytesIO()
            img = img.convert('RGB')  # Ensure compatibility with WebP format
            img.save(img_io, format='WEBP', quality=90, method=6)  # High quality, efficient compression
            
            # Replace the original image with the WebP version
            webp_image_name = os.path.splitext(self.image.name)[0] + '.webp'
            self.image.save(webp_image_name, ContentFile(img_io.getvalue()), save=False)
        
        # Call the parent save method
        super().save(*args, **kwargs)

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
    membership = models.CharField(max_length=255)  # Course name (e.g., 'OGS', 'LS', etc.)
    level = models.CharField(max_length=20)  # Level (e.g., 'OGS501', 'LS502', etc.)
    # If 'training_sections' is meant to represent sublevels, you can keep it; otherwise, you may remove it
    training_sections = models.IntegerField(default=3)  # Default sections (if applicable)
    purchased_at = models.DateTimeField(auto_now_add=True)  # Timestamp for purchase time
    status = models.IntegerField(default=0, choices=[(i, str(i)) for i in range(101)])  # Completion percentage (0 to 100)

    def update_progress(self, membership, level, video_id):
        # Get the video instance by the passed-in video_id
        video = membershipVideo.objects.get(id=video_id)

        # Filter the videos using the provided membership and level
        videos = membershipVideo.objects.filter(membership=membership, level=level)
        
        total_videos = videos.count()  # Total number of videos in this level
        
        # Count how many videos the user has completed (via UserVideoProgress)
        completed_videos = UserVideoProgress.objects.filter(user=self.user, video__in=videos, completed=True).count()

        # Calculate the progress as a percentage
        if total_videos > 0:
            progress = (completed_videos / total_videos) * 100
        else:
            progress = 0  # If there are no videos, consider 0% completion

        # Update the course completion status (percentage)
        self.status = int(progress)  # Convert to an integer percentage
        self.save()

        

    class Meta:
        verbose_name = "User Membership Level"
        verbose_name_plural = "User Membership Levels"
        unique_together = ('user', 'membership', 'level', 'training_sections')  # Unique constraint to prevent duplicates

    def __str__(self):
        return f"{self.user.username} - {self.membership} - {self.level} - {self.status}%"
        




class membershipVideo(models.Model):
    LEVEL_CHOICES = [
        ('OGS501', 'Level 1 - OGS501'),
        ('OGS502', 'Level 2 - OGS502'),
        ('LS501', 'Level 1 - LS501'),
        ('LS502', 'Level 2 - LS502'),
        ('PM501', 'Level 1 - PM501'),
        ('PM502', 'Level 2 - PM502'),
    ]

    COURSE_CHOICES = [
        ('OGS', 'Organization Growth Strategies'),
        ('LS', 'Leadership'),
        ('PM', 'Principles of Ministry'),
    ]

    # ForeignKey to the Membership model
    membership = models.ForeignKey(Membership, related_name='videos', on_delete=models.CASCADE)
    
    # Video details
    title = models.CharField(max_length=255)
    description = models.TextField()

    # File field for video upload
    video_file = models.FileField(upload_to='videos/%Y/%m/%d/', blank=True, null=True)

    # Level for the video (Level 1 or Level 2)
    level = models.CharField(max_length=300, choices=LEVEL_CHOICES)

    def __str__(self):
        return f"{self.title} ({self.level})"

    @property
    def full_course_name(self):
        """Returns the full course name without the level."""
        # Get the full course name from COURSE_CHOICES
        return dict(self.COURSE_CHOICES).get(self.membership.course_name, "Unknown Course")

    class Meta:
        verbose_name = "Video"
        verbose_name_plural = "Videos"
        


class UserVideoProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # Link to the user
    video = models.ForeignKey(membershipVideo, on_delete=models.CASCADE)  # Link to the video
    completed = models.BooleanField(default=False)  # Track if the user has completed the video

    class Meta:
        unique_together = ('user', 'video')  # Enforce uniqueness for user-video pairs

    def __str__(self):
        return f"{self.user.username} - {self.video.title} - {'Completed' if self.completed else 'Not Completed'}"

