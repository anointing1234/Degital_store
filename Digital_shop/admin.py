from django.contrib import admin
from .models import background_slider_images,Products,PasswordResetCode,Cart,CartItem,Membership,UserMembershipLevel
from django.utils.html import format_html

@admin.register(Products)
class ProductsAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_type', 'price', 'product_file_link', 'is_featured', 'purchased_by_list', 'created_at')
    list_filter = ('product_type',)

    # This method will create a clickable link to the product file
    def product_file_link(self, obj):
        if obj.product_file:
            return format_html('<a href="{}" target="_blank">Download/View</a>', obj.product_file.url)
        return "No file"

    product_file_link.short_description = 'Product File'  # This will show as the column header

    # Custom method to display the users who purchased the product
    def purchased_by_list(self, obj):
        return ", ".join([user.username for user in obj.purchased_by.all()])

    purchased_by_list.short_description = 'Purchased By' 
    

# Register your models here.
@admin.register(background_slider_images)
class background_slider_imagesAdmin(admin.ModelAdmin):
    list_display = ('order',)  # Display heading and order in the admin list
    ordering = ('order',)


    

class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 1  # Number of empty forms to display

class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at')  # Display these fields in the list view
    search_fields = ('user__username',)  # Search by username
    inlines = [CartItemInline]  # Inline editing for CartItems


# Optionally, you can also register CartItem if you want to manage them independently
@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'quantity')  # Fields to display in the list view
    search_fields = ('cart__user__username', 'product__name') 




@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('course_name', 'level_1_price', 'level_2_price', 'training_sections','purchased_by_list')
    list_filter = ('course_name',)
    search_fields = ('course_name', 'level_1', 'level_2')
    filter_horizontal = ('purchased_by',)  # Adds a widget for ManyToManyField

    def purchased_by_list(self, obj):
        """Display users who purchased this membership."""
        return ", ".join([user.username for user in obj.purchased_by.all()])
    
    purchased_by_list.short_description = "Purchased By"



class UserMembershipLevelAdmin(admin.ModelAdmin):
    list_display = ('user', 'membership', 'level', 'training_sections', 'purchased_at')
    search_fields = ('user__username', 'membership__course_name', 'level')
    list_filter = ('membership', 'level', 'user')
    ordering = ('-purchased_at',)
    list_editable = ('training_sections',)




# Register UserMembershipLevel
admin.site.register(UserMembershipLevel, UserMembershipLevelAdmin)
admin.site.register(Cart, CartAdmin)    
# admin.site.register(PasswordResetCode)    