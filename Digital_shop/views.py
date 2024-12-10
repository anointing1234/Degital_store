from django.shortcuts import render,redirect, get_object_or_404
from .models import Products,background_slider_images,Cart,CartItem,Membership,UserMembershipLevel,membershipVideo,UserVideoProgress
import requests
from requests.exceptions import ConnectionError, Timeout, RequestException
import random
from django.conf import settings
import stripe 
from django.views import View
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import logout, authenticate,login as django_login
from .forms import RegisterForm,PasswordResetForm,PasswordResetConfirmForm
from django.contrib.auth.forms import AuthenticationForm
from paystackapi.paystack import Paystack
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from .models import PasswordResetCode
import secrets
from datetime import timedelta
from django.core.mail import send_mail
from django.utils import timezone
from django.http import JsonResponse
import json
import logging
from paystackapi.transaction import Transaction  
import time
from django.db.models import Case, When





logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)





# Set Stripe's API key
stripe.api_key = settings.STRIPE_SECRET_KEY
paystack = Paystack(secret_key=settings.PAYSTACK_SECRET_KEY)



def handle_item_payment(request):
    if request.method == 'POST':
        cart_item_ids = request.POST.get('cart_item_ids')  # Get the cart item IDs from the form
        payment_method = request.POST.get('payment_method')

        # Split the cart item IDs into a list
        cart_item_id_list = cart_item_ids.split(',')
        print("Cart Item IDs:", cart_item_id_list)  # Debugging output

        # Initialize a list to hold the products
        products = []

        # Retrieve cart items based on the IDs
        for cart_item_id in cart_item_id_list:
            try:
                cart_item = CartItem.objects.get(pk=cart_item_id)  # Get the CartItem instance
                products.append(cart_item.product)  # Access the associated Product
            except CartItem.DoesNotExist:
                print(f"CartItem with ID {cart_item_id} does not exist.")
                return redirect('cart')  # Handle the error as needed

        if payment_method == 'stripe':
            # Redirect to Stripe payment handler
            if len(products) == 1:
                return redirect('create-checkout-session', pk=products[0].pk)  # Use the primary key of the single product
            else:
                return redirect('create-checkout-sessions', product_ids=','.join(str(product.pk) for product in products))  # Join the primary keys of multiple products
        
        elif payment_method == 'paystack':
            # Redirect to Paystack payment handler
            if len(products) == 1:
                return redirect('create-paystack-transaction', pk=products[0].pk)  # Use the primary key of the single product
            else:
                return redirect('create-paystack-transactions', product_ids=','.join(str(product.pk) for product in products))  # Join the primary keys of multiple products
        
        else:
            # Handle invalid payment method
            return redirect('cart')


class CreateStripeCheckoutSessionsView(View):
    def get(self, request, *args, **kwargs):
        user = request.user
        # Get the user's cart
        cart = get_object_or_404(Cart, user=user)
        line_items = []
        product_metadata = {}

        # Iterate over cart items and add them to Stripe's line items
        for item in cart.cart_items.all():
            product = item.product
            image_url = f"{settings.BACKEND_DOMAIN}{product.image.url}"
            price_in_ngn = Decimal(product.price)
            exchange_rate = self.get_exchange_rate()

            if exchange_rate is None:
                return render(request, "network_error.html", {"message": "Network error while fetching exchange rate. Please try again later."})

            price_in_usd = price_in_ngn * Decimal(str(exchange_rate))
            price_in_usd_cents = int(price_in_usd * 100)

            line_items.append({
                'price_data': {
                    'currency': 'usd',
                    'unit_amount': price_in_usd_cents,
                    'product_data': {
                        'name': product.name,
                        'description': product.desc,
                        'images': [image_url],
                    },
                },
                'quantity': item.quantity,  # Use the quantity from the CartItem
            })

            # Collect metadata for each cart item
            product_metadata[f"product_{product.id}"] = product.id

        try:
            # Create Stripe checkout session with multiple line items and cart metadata
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=line_items,
                mode='payment',
                success_url=f"{settings.BACKEND_DOMAIN}/success_stripe/?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=settings.PAYMENT_CANCEL_URL,
                metadata=product_metadata  # Add product metadata
            )
            return redirect(checkout_session.url)

        except Exception as e:
            return render(request, "error.html", {"message": str(e)} )

    def get_exchange_rate(self):
        # Fetch exchange rates from the API
        api_key = '3d5eeb185c2d6cae6b985e03'  # Your ExchangeRate-API key
        exchange_url = f'https://v6.exchangerate-api.com/v6/{api_key}/latest/NGN'

        try:
            response = requests.get(exchange_url, timeout=10)
            response.raise_for_status()  # Raise HTTPError for bad responses
            data = response.json()
            if 'conversion_rates' in data and 'USD' in data['conversion_rates']:
                return Decimal(data['conversion_rates']['USD'])  # Return NGN to USD rate as Decimal
            else:
                raise ValueError("Invalid response from exchange rate API")

        except requests.exceptions.ConnectionError:
            print("Network error: Unable to connect to the exchange rate API.")
        except requests.exceptions.Timeout:
            print("Network error: The request to the exchange rate API timed out.")
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
        except Exception as e:
            print(f"Error fetching exchange rate: {e}")
        
        # Return None in case of errors to handle it in the calling function
        return None



def payment__stripe_success(request):
    # Retrieve the session ID from the GET parameters
    session_id = request.GET.get('session_id')

    if not session_id:
        # Redirect to the homepage or show an error if session_id is not found
        return redirect('home')

    try:
        # Retrieve the Stripe checkout session
        session = stripe.checkout.Session.retrieve(session_id)

        # Retrieve product IDs from session metadata
        product_ids = [session.metadata[key] for key in session.metadata if key.startswith('product_')]

        if not product_ids:
            # If no product_ids are found, handle the error
            return redirect('home')

        # Fetch the user's cart
        user = request.user
        cart = get_object_or_404(Cart, user=user)

        # Get the purchased cart items (based on product_ids)
        cart_items = cart.cart_items.filter(product_id__in=product_ids)

        # Add the products to the user's purchased products (assuming you have such a mechanism)
        for item in cart_items:
            product = item.product
            product.purchased_by.add(user)

        # Remove the purchased items from the cart
        cart_items.delete()

        # Render the success page with the purchased products
        return render(request, 'success.html', {'products': [item.product for item in cart_items]})

    except stripe.error.InvalidRequestError:
        # Handle any Stripe-related errors here, such as an invalid session
        return redirect('home')

    except Exception as e:
        # Handle any other unexpected exceptions
        print(f"Error retrieving session: {e}")
        return redirect('home')






class CreatePaystackTransactionsView(View):
    def get(self, request, *args, **kwargs):
        cart = get_object_or_404(Cart, user=request.user)  # Get the user's cart
        user_email = request.user.email
        total_amount = 0
        product_ids = []  # To store product IDs for the metadata

        # Loop through the cart items and calculate the total amount
        for cart_item in cart.cart_items.all():
            product = cart_item.product
            product_ids.append(str(product.id))
            total_amount += int(product.price * cart_item.quantity * 100)  # Convert to kobo for Paystack

        # If no products in the cart, redirect to the cart page
        if not product_ids:
            return redirect('cart')  # Replace with your cart page URL

        logger.info(f"Cart Item IDs: {product_ids}")
        logger.info(f"Total Amount (in kobo): {total_amount}")

        # Initialize the Paystack transaction
        try:
            # Prepare the parameters for the Paystack API call
            timestamp = int(time.time())  # Get the current timestamp
            reference = f'PAYSTACK-{"-".join(product_ids)}-{request.user.id}-{timestamp}'  # Append timestamp
            params = {
                'email': user_email,
                'amount': total_amount,
                'reference': reference,
                'callback_url': f"{settings.BACKEND_DOMAIN}/paystack_success/success/",
                'metadata': {'product_ids': ','.join(product_ids)}  # Store product IDs in metadata
            }
            logger.info(f"Paystack API Request Parameters: {params}")

            response = Transaction.initialize(**params)  # Adjust based on your Paystack API wrapper

            logger.info(f"Paystack API response: {response}")

            # Check if the response contains an 'error' key
            if 'error' in response:
                logger.error(f"Paystack API error: {response['error']}")
                return render(request, "error.html", {"message": response['error']})

            # Check if the response contains a 'data' key
            if 'data' in response:
                checkout_url = response['data']['authorization_url']
                return redirect(checkout_url)
            else:
                logger.error("Paystack API response missing 'data' key")
                return render(request, "error.html", {"message": "An error occurred. Please try again later."})

        except requests.ConnectionError:
            logger.error("Network error: Unable to connect to Paystack")
            return render(request, "error.html", {"message": "Network error: Unable to connect to Paystack. Please check your internet connection."})
        except requests.Timeout:
            logger.error("Network error: The request to Paystack timed out")
            return render(request, "error.html", {"message": "Network error: The request to Paystack timed out. Please try again."})
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return render(request, "error.html", {"message": str(e)})




def paystack_success2(request):
    reference = request.GET.get('reference')

    if not reference:
        return redirect('home')

    try:
        # Verify the transaction with Paystack
        response = paystack.transaction.verify(reference)

        if response['data']['status'] == 'success':
            # Retrieve product IDs from the transaction metadata
            product_ids = response['data']['metadata']['product_ids'].split(',')
            user = request.user
            cart = get_object_or_404(Cart, user=user)

            purchased_products = []

            # Loop through the purchased product IDs and process them
            for product_id in product_ids:
                product = get_object_or_404(Products, id=product_id)
                product.purchased_by.add(user)  # Assuming a ManyToManyField for purchased products
                purchased_products.append(product)

                # Remove the cart item after purchase
                cart_item = cart.cart_items.filter(product=product).first()
                if cart_item:
                    cart_item.delete()  # Remove the purchased item from the cart

            # Optionally: If all items in the cart are purchased, you can clear the entire cart
            # cart.cart_items.all().delete()

            # Render the success page with the purchased products
            return render(request, 'success.html', {'products': purchased_products})

        # If transaction failed, redirect to homepage
        return redirect('home')

    except Exception as e:
        print(f"Error verifying transaction: {e}")
        return redirect('home')



def handle_payment(request, product_id):
    product = get_object_or_404(Products, pk=product_id)
    payment_method = request.POST.get('payment_method')

    if payment_method == 'stripe':
        # Redirect to Stripe payment handler
        return redirect('create-checkout-session', pk=product.pk)
    
    elif payment_method == 'paystack':
        # Redirect to Paystack payment handler
        return redirect('create-paystack-transaction', pk=product.pk)
    
    else:
        # Handle invalid payment method
        return redirect('all-products')


class CreateStripeCheckoutSessionView(View):
    def get(self, request, *args, **kwargs):
        # Get the product based on its ID (passed as pk)
        product = get_object_or_404(Products, id=self.kwargs["pk"])
        image_url = f"{settings.BACKEND_DOMAIN}{product.image.url}"
        print(image_url)
        

        # Fetch the current exchange rate from NGN to USD
        exchange_rate = self.get_exchange_rate()

        # Convert the product price from NGN to USD
        price_in_ngn = Decimal(product.price)  # Ensure product price is a Decimal
        price_in_usd = price_in_ngn * Decimal(str(exchange_rate))  # Convert exchange_rate to Decimal  # Use Decimal for multiplication
        price_in_usd_cents = int(price_in_usd * 100)  # Stripe uses cents

        try:
            # Create Stripe checkout session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'unit_amount': price_in_usd_cents,  # Price in cents
                        'product_data': {
                            'name': product.name,
                            'description': product.desc,
                            'images': [image_url],
                        },
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f"{settings.BACKEND_DOMAIN}/success/?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=settings.PAYMENT_CANCEL_URL,
                metadata={
                    'product_id': product.id,  # Pass the product ID to metadata
                }
            )
            return redirect(checkout_session.url)

        except Exception as e:
            return render(request, "error.html", {"message": str(e)})

    def get_exchange_rate(self):
        # Fetch exchange rates from the API
        api_key = '3d5eeb185c2d6cae6b985e03'  # Your ExchangeRate-API key
        exchange_url = f'https://v6.exchangerate-api.com/v6/{api_key}/latest/NGN'  # Get rates based on NGN

        try:
            response = requests.get(exchange_url)
            data = response.json()
            if 'conversion_rates' in data and 'USD' in data['conversion_rates']:
                return Decimal(data['conversion_rates']['USD'])  # Return the NGN to USD rate as Decimal
            else:
                raise ValueError("Invalid response from exchange rate API")
        except Exception as e:
            print(f"Error fetching exchange rate: {e}")
            return Decimal(1)
        
        
        
        

class CreatePaystackTransactionView(View):
    def get(self, request, *args, **kwargs):
        product = get_object_or_404(Products, id=self.kwargs["pk"])
        user_email = request.user.email
        amount = int(product.price * 100)  # Paystack uses kobo

        try:
            reference = f'PAYSTACK_{product.id}_{request.user.id}_{int(time.time())}'
            response = paystack.transaction.initialize(
                email=user_email,
                amount=amount,
                reference=reference,
                callback_url=f"{settings.BACKEND_DOMAIN}/paystack/success/",
                metadata={'product_id': product.id},
            )
            logger.info(f"Paystack API response: {response}")

            if 'error' in response:
                logger.error(f"Paystack API error: {response['error']}")
                return render(request, "error.html", {"message": response['error']})

            if 'data' in response:
                checkout_url = response['data']['authorization_url']
                return redirect(checkout_url)
            else:
                logger.error("Paystack API response missing 'data' key")
                return render(request, "error.html", {"message": "An error occurred. Please try again later."})

        except requests.ConnectionError:
            logger.error("Network error: Unable to connect to Paystack")
            return render(request, "error.html", {"message": "Network error: Unable to connect to Paystack. Please check your internet connection."})
        except requests.Timeout:
            logger.error("Network error: The request to Paystack timed out")
            return render(request, "error.html", {"message": "Network error: The request to Paystack timed out. Please try again."})
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return render(request, "error.html", {"message": str(e)})
        



@login_required
def paystack_success(request):
    reference = request.GET.get('reference')

    if not reference:
        return redirect('home')

    try:
        # Verify the transaction
        response = paystack.transaction.verify(reference)
        if response['data']['status'] == 'success':
            product_id = response['data']['metadata']['product_id']
            product = get_object_or_404(Products, id=product_id)
            user = request.user

            # Add product to user's purchased products
            product.purchased_by.add(user)

            # Show success page
            return render(request, 'success.html', {'product': product})

        return redirect('home')

    except Exception as e:
        print(f"Error verifying transaction: {e}")
        return redirect('home')


def payment_success(request):
    # Retrieve the session ID from the GET parameters
    session_id = request.GET.get('session_id')

    if not session_id:
        # Redirect to the homepage or show an error if session_id is not found
        return redirect('home')

    try:
        # Retrieve the Stripe checkout session
        session = stripe.checkout.Session.retrieve(session_id)

        # Extract the product ID from the session metadata
        product_id = session.metadata.get('product_id')

        if not product_id:
            # If product_id is not in the metadata, handle the error
            return redirect('home')

        # Fetch the product using the product_id from your database
        product = get_object_or_404(Products, id=product_id)

        # Get the current user
        user = request.user

        # Add the product to the user's purchased products
        product.purchased_by.add(user)

        # Render the success page with the purchased product
        return render(request, 'success.html', {'product': product})

    except stripe.error.InvalidRequestError:
        # Handle any Stripe-related errors here, such as an invalid session
        return redirect('home')

    except Exception as e:
        # Handle any other unexpected exceptions
        print(f"Error retrieving session: {e}")
        return redirect('home')




@login_required
def library(request):
    user = request.user
    # Get all products purchased by the user
    purchased_products = user.purchased_products.all()

    context = {
        'purchased_products': purchased_products
    }
    return render(request, 'Digital_library.html', context)



def login(request):
    form = AuthenticationForm()
    return render(request,'registeration/login.html', {'form': form})

def register(request):
    form = RegisterForm()
    return render(request,'registeration/register.html',{'form': form})

# Create your views here.





# User Registration View
def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')  # Redirect to login after registration
        else:
           request.session['registration_errors'] = 'There was an error with your registration. Please correct the errors below.'
    else:
        form = RegisterForm()
    
    return render(request, 'registeration/register.html', {'form': form})




def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                django_login(request,user)  # Correct usage of Django's login function
                return redirect('home')  # Redirect to homepage after login
            else:
                messages.error(request, 'Invalid username or password. Please try again.', extra_tags='login')
        else:
            messages.error(request, 'Invalid username or password. Please try again.', extra_tags='login')
    else:
        form = AuthenticationForm()

    return render(request, 'registeration/login.html', {'form': form})


def custom_logout_view(request):
    logout(request)  # Log the user out
    return redirect('home')

def home(request):
    books = Products.objects.filter(product_type='book')
    videos = Products.objects.filter(product_type='video')
    audios = Products.objects.filter(product_type='audio')
    featured_books = Products.objects.filter(product_type='book', is_featured=True)
    featured_videos = Products.objects.filter(product_type='video', is_featured=True)
    featured_audios = Products.objects.filter(product_type='audio', is_featured=True)
    
    slides = background_slider_images.objects.all()
    # Fetch only the featured products
    featured_products = Products.objects.filter(is_featured=True)

    context = {
        'books': books,
        'videos': videos,
        'audios': audios,
        'featured_books': featured_books,
        'featured_videos': featured_videos,
        'featured_audios': featured_audios,
        'slides': slides
    }
    return render(request,'index.html',context)



    return redirect('home')  # Redirect to the home page or any other page


def sendpasswordresetmail(request):
    form = PasswordResetForm()
    return render(request,'registeration/send_password_email.html',{'form':form})




def request_password_reset(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']

            # Check if the email exists
            if User.objects.filter(email=email).exists():
                # Generate a random 6-digit number as the reset code
                reset_code = random.randint(100000, 999999)
                expires_at = timezone.now() + timedelta(hours=1)

                # Store the reset code in the database
                PasswordResetCode.objects.create(email=email, reset_code=str(reset_code), expires_at=expires_at)

                # Send email with the reset code
                send_mail(
                    'Your Password Reset Code',
                    f'Your password reset code is: {reset_code} expires in 1 hour',
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )

                # Show success message
                messages.success(request, 'Password reset code sent successfully!', extra_tags='send_success')
                return redirect('reset_password_page')  # Redirect to a success page
            else:
                # Show error message if the email doesn't exist
                messages.error(request, 'No user found with this email address.', extra_tags='error')
    else:
        form = PasswordResetForm()

    return render(request, 'send_password_reset.html', {'form': form})



def reset_password_page(request):
    form = PasswordResetConfirmForm()
    return render(request,'registeration/reset_password.html',{'form':form})



def confirm_password_reset(request):
    if request.method == 'POST':
        form = PasswordResetConfirmForm(request.POST)
        if form.is_valid():
            reset_code = form.cleaned_data['reset_code']
            new_password = form.cleaned_data['new_password']
            
            

            # Check if the reset code is valid and not expired
            try:
                reset_entry = PasswordResetCode.objects.get(reset_code=reset_code)

                if reset_entry.is_expired():
                    messages.error(request, 'The reset code has expired.')
                else:
                    # Reset password
                    user = User.objects.get(email=reset_entry.email)
                    user.set_password(new_password)
                    user.save()

                    # Invalidate the used reset code
                    reset_entry.delete()
                    messages.success(request, 'Password has been reset successfully!',extra_tags='reset')
                    return redirect('login')  # Redirect to login after successful reset
            except PasswordResetCode.DoesNotExist:
                messages.error(request, 'Invalid reset code.', extra_tags='reset')

    else:
        form = PasswordResetConfirmForm()

    return render(request,'registeration/reset_password.html',{'form': form})

def cart(request):
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)  # Get or create the user's cart
        cart_items = cart.cart_items.all()  # Get all items in the cart
        
        # Calculate the total amount using the get_total_price method
        total_amount = sum(item.get_total_price() for item in cart_items)
    else:
        cart_items = []
        total_amount = 0  # Set total amount to 0 if user is not authenticated

    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'total_amount': total_amount,  # Pass total amount to the template
    })


def remove_cart_item(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id)
    cart_item.delete()  # Remove the item from the cart
    return redirect('cart')



@login_required(login_url='login')
def add_to_cart(request, product_id):
    if request.method == 'POST':
        try:
            product = Products.objects.get(id=product_id)
            cart, created = Cart.objects.get_or_create(user=request.user)
            cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
            cart_item.quantity += 1
            cart_item.save()

            # Calculate updated cart count and total
            cart_count = cart.cart_items.count()
            cart_total = sum(item.product.price * item.quantity for item in cart.cart_items.all())

            return JsonResponse({'success': True, 'cart_count': cart_count, 'cart_total': cart_total})
        except Products.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Product not found.'}, status=404)
    return JsonResponse({'success': False}, status=400)




def cancel(request):
    return render(request,'cancel.html')




def custom_404_view(request, exception):
    return render(request, '404.html', status=404)

def custom_500_view(request):
    return render(request, '500.html', status=500)




def training_view(request):
    memberships = Membership.objects.annotate(
        course_order=Case(
            When(course_name='OGS', then=0),
            When(course_name='LS', then=1),
            When(course_name='PM', then=2),
            default=3,
        )
    ).order_by('course_order')
    return render(request, 'Training.html', {'memberships': memberships})



def pay_master(request):
    if request.method == 'POST':
        membership_id = request.POST.get('membership_id')
    else:
        membership_id = request.GET.get('membership_id')
        
    membership = get_object_or_404(Membership, id=membership_id)
            
    return render(request,'pay_master.html',{'membership': membership})

def membership_payment(request):
    if request.method == 'POST':
        membership_id = request.POST.get('membership_id')
        level = request.POST.get('level')
        payment_method = request.POST.get('payment_method')
        
        logger.info(f"Received payment request. Membership ID: {membership_id}, Level: {level}, Payment Method: {payment_method}")

        # Get the Membership object using the membership_id
        membership = get_object_or_404(Membership, id=membership_id)
        course_name_full = membership.get_course_name_display()  # Get the full name of the course
        logger.info(f"Membership found. Course: {course_name_full}, Level 1: {membership.level_1}, Level 2: {membership.level_2}")

        # Extract the levels for this membership
        level_1 = membership.level_1
        level_2 = membership.level_2

        # Check if the user has already purchased the level
        existing_membership = UserMembershipLevel.objects.filter(
            user=request.user,
            membership=course_name_full,  # Use full course name
            level=level
        ).exists()

        if existing_membership:
            # If the user has already purchased this level, return an error message
            error_message = f"You have already purchased {course_name_full} - {level}."
            logger.warning(f"User {request.user} already purchased {course_name_full} - {level}. Error: {error_message}")
            return render(request, 'pay_master.html', {'membership': membership, 'error_message': error_message})

        # Check if the user is attempting to purchase Level 2
        elif level == level_2:  # This is a Level 2 course
            # Check if the user has already purchased Level 1 for the same course (membership)
            level_1_membership = UserMembershipLevel.objects.filter(
                user=request.user,
                membership=course_name_full,  # Use full course name
                level=level_1
            ).exists()
            if not level_1_membership:
                # If Level 1 has not been completed, return an error message
                error_message = (
                    f"You need to complete {course_name_full} - {level_1} "
                    f"before purchasing {course_name_full} - {level_2}."
                )
                logger.warning(f"User {request.user} attempted to purchase {course_name_full} - {level_2} without completing Level 1. Error: {error_message}")
                return render(request, 'pay_master.html', {'membership': membership, 'error_message': error_message})

        # If the user is eligible to purchase the level, proceed to payment
        if payment_method == 'stripe':
            logger.info(f"User {request.user} selected Stripe for payment. Redirecting to Stripe payment page.")
            return redirect('stripe_membership_payment', pk=membership_id, level=level)
        elif payment_method == 'paystack':
            logger.info(f"User {request.user} selected Paystack for payment. Redirecting to Paystack payment page.")
            return redirect('paystack_membership_payment', pk=membership_id, level=level)

    # If method is not POST, redirect to the payment master page
    logger.info(f"Non-POST request received. Redirecting to payment master page.")
    return redirect('pay_master')



class StripeMembershipCheckoutSession(View):
    def get(self, request, *args, **kwargs):
        membership_id = kwargs.get('pk')  
        level = kwargs.get('level')  

        # Log the received 'level' parameter
        logger.info(f"Received level parameter: {level}")

        
        # Get the membership object
        membership = get_object_or_404(Membership, id=membership_id)
        
           # Log the membership levels
        logger.info(f"Membership object: {membership}")
        logger.info(f"Membership Level 1: {membership.level_1}")
        logger.info(f"Membership Level 2: {membership.level_2}")

        # Determine price based on selected level
        if level == membership.level_1:
            price_in_ngn = membership.level_1_price
        elif level == membership.level_2:
            price_in_ngn = membership.level_2_price   
        else:
            return render(request, "error.html", {"message": "Invalid membership level selected."})

        # Fetch exchange rate and calculate USD price
        exchange_rate = self.get_exchange_rate()
        if exchange_rate is None:
            return render(request, "network_error.html", {
                "message": "Unable to fetch exchange rate. Please try again later."
            })

        price_in_usd = Decimal(price_in_ngn) * Decimal(str(exchange_rate))
        price_in_usd_cents = int(price_in_usd * 100)

        # Create Stripe checkout session
        try:
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'unit_amount': price_in_usd_cents,
                        'product_data': {
                            'name': f"{membership.course_name} - {level}",
                            'description': f"Enrollment for {membership.course_name}, {level}",
                        },
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f"{settings.BACKEND_DOMAIN}/success_stripe_membership/?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=settings.PAYMENT_CANCEL_URL,
                metadata={
                    'membership_id': membership_id,
                    'level': level,
                }
            )
            return redirect(checkout_session.url)
        except Exception as e:
            return render(request, "error.html", {"message": f"Error creating Stripe checkout session: {str(e)}"})

    def get_exchange_rate(self):
        # Fetch exchange rates from the API
        api_key = '3d5eeb185c2d6cae6b985e03'  # Your ExchangeRate-API key
        exchange_url = f'https://v6.exchangerate-api.com/v6/{api_key}/latest/NGN'

        try:
            response = requests.get(exchange_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if 'conversion_rates' in data and 'USD' in data['conversion_rates']:
                return Decimal(data['conversion_rates']['USD'])
            else:
                raise ValueError("Invalid response from exchange rate API")
        except Exception as e:
            print(f"Error fetching exchange rate: {e}")
            return None



class PaystackMembershipcheckoutSession(View):
    def get(self, request, *args, **kwargs):
        # Retrieve membership and level from URL parameters
        membership_id = kwargs.get('pk')  # Membership ID from URL
        level = kwargs.get('level')  # Membership level from URL

        # Log the received level and membership_id for debugging
        logger.info(f"Received membership_id: {membership_id}, level: {level}")

        # Get the membership object
        membership = get_object_or_404(Membership, id=membership_id)

        # Log the membership levels
        logger.info(f"Membership object: {membership}")
        logger.info(f"Membership Level 1: {membership.level_1}")
        logger.info(f"Membership Level 2: {membership.level_2}")

        # Determine the price based on the selected level
        if level == membership.level_1:
            price_in_ngn = membership.level_1_price
        elif level == membership.level_2:
            price_in_ngn = membership.level_2_price
        else:
            logger.warning(f"Invalid level selected: {level}. Expected level_1: {membership.level_1}, level_2: {membership.level_2}")
            return render(request, "error.html", {"message": "Invalid membership level selected."})

        # Log the determined price
        logger.info(f"Price in NGN: {price_in_ngn}")

        user_email = request.user.email
        amount = int(price_in_ngn * 100)  # Paystack uses kobo (100 kobo = 1 NGN)

        try:
            reference = f'PAYSTACK_{membership.id}_{request.user.id}_{int(time.time())}'
            response = paystack.transaction.initialize(
                email=user_email,
                amount=amount,
                reference=reference,
                callback_url=f"{settings.BACKEND_DOMAIN}/paystack_membership/success/",
                metadata={
                    'membership_id': membership_id,
                    'level': level,
                },
            )
            logger.info(f"Paystack API response: {response}")

            if 'error' in response:
                logger.error(f"Paystack API error: {response['error']}")
                return render(request, "error.html", {"message": response['error']})

            if 'data' in response:
                checkout_url = response['data']['authorization_url']
                return redirect(checkout_url)
            else:
                logger.error("Paystack API response missing 'data' key")
                return render(request, "error.html", {"message": "An error occurred. Please try again later."})

        except requests.ConnectionError:
            logger.error("Network error: Unable to connect to Paystack")
            return render(request, "error.html", {"message": "Network error: Unable to connect to Paystack. Please check your internet connection."})
        except requests.Timeout:
            logger.error("Network error: The request to Paystack timed out")
            return render(request, "error.html", {"message": "Network error: The request to Paystack timed out. Please try again."})
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return render(request, "error.html", {"message": str(e)})


def success_stripe_membership(request):
    session_id = request.GET.get('session_id')

    if not session_id:
        # Redirect if no session ID is provided
        return redirect('pay_master')

    try:
        # Retrieve the session object from Stripe using the session_id
        session = stripe.checkout.Session.retrieve(session_id)

        # Check if the payment was successful
        if session.payment_status == 'paid':
            # Extract metadata from the session
            membership_id = session.metadata['membership_id']
            level = session.metadata['level']

            # Get the Membership object based on the membership ID
            membership = get_object_or_404(Membership, id=membership_id)

            # Get the current user
            user = request.user

            # Get the full name of the course based on the `course_name` short code
            course_name_full = dict(Membership.COURSE_CHOICES).get(membership.course_name, membership.course_name)

            # Check if the user already has this membership level
            if not UserMembershipLevel.objects.filter(user=user, membership=course_name_full, level=level).exists():
                # Create a new UserMembershipLevel record
                user_membership_level = UserMembershipLevel(
                    user=user,
                    membership=course_name_full,
                    level=level,
                    training_sections=3,  # Adjust this based on your actual needs
                )
                user_membership_level.save()

                # Add the user to the purchased_by field of the membership
                membership.purchased_by.add(user)
                membership.save()

                # Log the successful addition
                logger.info(f"User {user.username} successfully purchased {course_name_full} - {level}.")

                # Show success message
                messages.success(request, f"Congratulations! You have successfully purchased {course_name_full} - {level}.")

                # Pass the course full name and level to the template
                return render(request, 'membership_success.html', {
                    'course_name': course_name_full,
                    'level': level,
                })

            else:
                # If user already has the membership level, show a message
                messages.warning(request, f"You have already purchased {course_name_full} - {level}.")
                return render(request, 'already_purchased.html')

        else:
            # If payment is not successful
            messages.error(request, "Payment failed. Please try again.")
            return redirect('home')

    except stripe.error.StripeError as e:
        # Log the error and show a message if any Stripe error occurs
        logger.error(f"Error verifying Stripe transaction: {e}")
        messages.error(request, "There was an error verifying your payment. Please try again.")
        return redirect('home')
    except Exception as e:
        # Log any other exception
        logger.error(f"Error processing Stripe payment: {e}")
        messages.error(request, "There was an unexpected error. Please try again.")
        return redirect('home')  



def paystack_membership(request):
    reference = request.GET.get('reference')

    if not reference:
        return redirect('pay_master')

    try:
        # Verify the transaction with Paystack
        response = paystack.transaction.verify(reference)

        if response['data']['status'] == 'success':
            membership_id = response['data']['metadata']['membership_id']
            level = response['data']['metadata']['level']

            # Fetch the Membership object
            membership = get_object_or_404(Membership, id=membership_id)
            user = request.user

            # Map course_name to full name using COURSE_CHOICES
            course_name_full = dict(Membership.COURSE_CHOICES).get(membership.course_name, membership.course_name)

            # Debugging to ensure correct mapping
            logger.info(f"Membership course_name: {membership.course_name}")
            logger.info(f"Resolved full course name: {course_name_full}")

            # Check if the user already has this membership level
            if not UserMembershipLevel.objects.filter(user=user, membership=course_name_full, level=level).exists():
                # Create UserMembershipLevel record
                user_membership_level = UserMembershipLevel(
                    user=user,
                    membership=course_name_full,
                    level=level,
                    training_sections=3,
                )
                user_membership_level.save()

                # Add user to membership's purchased_by
                membership.purchased_by.add(user)
                membership.save()

                logger.info(f"User {user.username} successfully purchased {course_name_full} - {level}.")
                messages.success(request, f"Congratulations! You have successfully purchased {course_name_full} - {level}.")

                return render(request, 'membership_success.html', {
                    'course_name': course_name_full,
                    'level': level,
                })
            else:
                messages.warning(request, f"You have already purchased {course_name_full} - {level}.")
                return render(request, 'already_purchased.html')

        else:
            messages.error(request, "Payment failed. Please try again.")
            return redirect('home')

    except Exception as e:
        logger.error(f"Error verifying Paystack transaction: {e}")
        messages.error(request, "There was an error verifying your payment. Please try again.")
        return redirect('home')


def dashboard(request):
    if request.user.is_authenticated:
        user_memberships = UserMembershipLevel.objects.filter(user=request.user)
        # Assume user_memberships contains a 'course_name' and 'level' field
        current_course = user_memberships.first().membership if user_memberships.exists() else "No Course Selected"
        current_level = user_memberships.first().level if user_memberships.exists() else "No Level Selected"
        current_progress = user_memberships.first().status if user_memberships.exists() else 0
    else:
        user_memberships = []
        current_course = "No Course Selected"
        current_level = "No Level Selected"
        current_progress = 0

    context = {
        'user_memberships': user_memberships,
        'current_course': current_course,
        'current_level': current_level,
        'current_progress': current_progress,
    }
    return render(request,"dashboard/index.html",context)


def Mycourses(request):
    if request.user.is_authenticated:
        # Fetch all memberships for the user, ordered by `purchased_at` (oldest to newest)
        user_memberships = UserMembershipLevel.objects.filter(user=request.user).order_by('purchased_at')

        if user_memberships.exists():
            # Find the first incomplete course, ordered by purchase date
            incomplete_membership = user_memberships.filter(status__lt=100).first()
            # Fallback to the last purchased course if all are complete
            current_membership = incomplete_membership if incomplete_membership else user_memberships.last()
            current_course = current_membership.membership
            current_level = current_membership.level
            current_progress = current_membership.status
        else:
            # Defaults if no memberships exist
            current_course = "No Course Selected"
            current_level = "No Level Selected"
            current_progress = 0
    else:
        # Defaults if the user is not authenticated
        user_memberships = []
        current_course = "No Course Selected"
        current_level = "No Level Selected"
        current_progress = 0

    # Pass data to the template
    context = {
        'user_memberships': user_memberships,
        'current_course': current_course,
        'current_level': current_level,
        'current_progress': current_progress,
    }
    return render(request, "dashboard/my_courses.html", context)




def get_course_status(request, course_key, level_code):
    # Ensure the user is logged in
    if not request.user.is_authenticated:
        logger.warning('User is not authenticated while attempting to access course status.')
        return JsonResponse({'success': False, 'message': 'User must be logged in to access course status'}, status=401)

    try:
        # Log user details and input values
        logger.info(f'Fetching course status for user: {request.user.username}, course_key: {course_key}, level_code: {level_code}')
        
        # Fetch the UserMembershipLevel instance based on the course and level
        membership_level = UserMembershipLevel.objects.get(user=request.user, membership=course_key, level=level_code)

        # Log the retrieved membership level details
        logger.info(f'Found membership level: {membership_level}')
        
        # Fetch the completion status from the `status` field
        completion_percentage = membership_level.status
        logger.info(f'Completion percentage for course {course_key} and level {level_code}: {completion_percentage}')

        # Return a JSON response with the completion status
        return JsonResponse({
            'success': True,
            'status': {
                'percentage': completion_percentage,
            }
        })

    except UserMembershipLevel.DoesNotExist:
        logger.error(f'Membership level not found for user: {request.user.username}, course_key: {course_key}, level_code: {level_code}')
        return JsonResponse({'success': False, 'message': 'User membership level not found for the specified course and level'})

    except Exception as e:
        logger.exception('An error occurred while fetching course status: %s', e)
        return JsonResponse({'success': False, 'message': 'An error occurred while fetching course status'})



def Training_center(request):
    videos = []
    membership_name = ""
    level_name = ""
    level_2_name = ""  # Initialize level_2_name to avoid undefined errors
    user_membership_status = None
    user_video_progress = {}  # Dictionary to store video progress
    level_2_purchased = False  # Initialize the variable for Level 2 purchase status

    if request.method == 'POST':
        # Retrieve membership and level from POST data
        membership_name = request.POST.get('membership')
        level_name = request.POST.get('level')

        # Log the membership and level received from the POST request
        logger.info(f"Received POST data: membership_name={membership_name}, level_name={level_name}")

        # Map full course name to short course code in Membership.COURSE_CHOICES
        course_code_dict = {name: code for code, name in Membership.COURSE_CHOICES}
        course_code = course_code_dict.get(membership_name, None)
        logger.info(f"Mapped course_name={membership_name} to course_code={course_code}")

        if course_code:
            # Fetch the membership object based on the course name
            membership_obj = Membership.objects.filter(course_name=course_code).first()
            if membership_obj:
                logger.info(f"Found membership object: {membership_obj}")

                # Fetch the UserMembershipLevel object related to the user, membership, and level
                user_membership_level = UserMembershipLevel.objects.filter(
                    user=request.user,
                    membership=membership_name,
                    level=level_name
                ).first()

                if user_membership_level:
                    user_membership_status = user_membership_level.status
                    logger.info(f"UserMembershipLevel status: {user_membership_status} for user {request.user.username}")
                else:
                    logger.info(f"No UserMembershipLevel found for user {request.user.username}, "
                                f"membership: {membership_obj}, level: {level_name}")

                # If the level is "Level 1", check if "Level 2" is purchased
                if level_name == membership_obj.level_1:  # Only check if level_name is Level 1
                    level_2_name = membership_obj.level_2  # Get Level 2 for this course
                    logger.info(f"Expected Level 2 name: {level_2_name}")

                    # Check if Level 2 is purchased for the user
                    user_level_2_membership = UserMembershipLevel.objects.filter(
                        user=request.user,
                        membership=membership_name,
                        level=level_2_name
                    ).first()

                    if user_level_2_membership:
                        level_2_purchased = True
                        logger.info(f"Level 2 is purchased for user {request.user.username}")
                    else:
                        level_2_purchased = False
                        logger.info(f"No Level 2 membership found for user {request.user.username} and membership {membership_name}")

                # Fetch videos for the current level
                videos = membershipVideo.objects.filter(
                    membership=membership_obj,
                    level=level_name  # Use the level_name directly, no mapping required
                )
                logger.info(f"Found {len(videos)} videos for membership {membership_obj} and level {level_name}")

                # Fetch user video progress for the retrieved videos
                video_ids = videos.values_list('id', flat=True)
                user_progress_records = UserVideoProgress.objects.filter(
                    user=request.user,
                    video_id__in=video_ids
                )
                user_video_progress = {
                    progress.video_id: progress.completed for progress in user_progress_records
                }
                logger.info(f"User video progress: {user_video_progress}")
            else:
                logger.info(f"No membership found for course_code={course_code}")
        else:
            logger.info(f"Invalid membership: course_code={course_code}")

    return render(request, "dashboard/Training_center.html", {
        'videos': videos,  # Videos for the current level
        'level_2_purchased': level_2_purchased,  # Pass the level_2_purchased variable
        'membership_name': membership_name,
        'level_name': level_name,
        'level_2_name': level_2_name,  # Pass the Level 2 name
        'user_membership_status': user_membership_status,
        'user_video_progress': user_video_progress,  # Pass progress to template
    })




def video_section(request):
    # Check if the form is submitted via POST request
    if request.method == 'POST':
        # Retrieve the necessary data from the POST request
        video_id = request.POST.get('video_id')
        course_name = request.POST.get('course_name')
        level = request.POST.get('level')

        # Log received data (Optional)
        logger.info(f"Received POST data: video_id={video_id}, course_name={course_name}, level={level}")

        # Fetch the video object using the video ID
        video = get_object_or_404(membershipVideo, id=video_id)

        # Validate if the provided course name and level match the video data
        if video.membership.course_name != course_name or video.level != level:
            logger.error("Invalid course or level data.")
            # Return an error page if there is a mismatch
            return render(request, 'dashboard/error.html', {
                'error_message': 'Invalid video course or level. Please try again.'
            })

        # Successfully found the video and data is valid, render the video page
        return render(request, "dashboard/video.html", {
            'video': video,
        })

    else:
        # If it's not a POST request, redirect or handle it accordingly
        logger.error("Invalid request method")
        return render(request, 'dashboard/error.html', {
            'error_message': 'Invalid request method. Please submit the form correctly.'
        })
        


def update_video_progress(request, video_id):
    try:
        logger.info(f"Fetching video with ID: {video_id} for user: {request.user.username}")
        
        # Fetch the video using the provided video_id
        video = membershipVideo.objects.get(id=video_id)
        logger.info(f"Video fetched successfully: {video.title}")
        
        # Create or get the progress for the video
        progress, created = UserVideoProgress.objects.get_or_create(user=request.user, video=video)
        logger.info(f"Progress {'created' if created else 'retrieved'} for video: {video.title}, User: {request.user.username}")
        
        # Mark as completed if not already marked
        if not progress.completed:
            progress.completed = True
            progress.save()
            logger.info(f"Video progress marked as completed for video: {video.title}, User: {request.user.username}")
        else:
            logger.info(f"Video progress was already marked as completed for video: {video.title}, User: {request.user.username}")

        # Use the video membership and level to update UserMembershipLevel
        membership_name = video.full_course_name  # Get full course name from membershipVideo's property
        level = video.level  # Get the video level
        
        # Update the UserMembershipLevel status
        try:
            membership_level = UserMembershipLevel.objects.get(
                user=request.user, 
                membership=membership_name,  # Pass the full course name
                level=level
            )
            membership_level.update_progress(membership=video.membership, level=level, video_id=video_id)
            logger.info(f"Updated progress for membership: {membership_name}, level: {level}. New status: {membership_level.status}%")
        except UserMembershipLevel.DoesNotExist:
            logger.error(f"UserMembershipLevel not found for user {request.user.username}, course name {membership_name}, level {level}")

        return JsonResponse({
            'status': 'success',
            'message': 'Video progress updated.',
            'progress_created': created  # Indicates if this is a new entry
        })

    except membershipVideo.DoesNotExist:
        logger.error(f"Video with ID: {video_id} not found for user: {request.user.username}")
        return JsonResponse({'status': 'error', 'message': 'Video not found.'}, status=404)

    except Exception as e:
        logger.exception(f"An unexpected error occurred while updating video progress for video ID: {video_id}")
        return JsonResponse({'status': 'error', 'message': 'An error occurred.'}, status=500)


def profile(request):
    user = request.user
    purchased_courses_count = UserMembershipLevel.objects.filter(user=user).count()
    completed_courses_count = UserMembershipLevel.objects.filter(user=user, status=100).count()
    memberships = UserMembershipLevel.objects.filter(user=request.user)
    return render(request,'dashboard/profile.html',{
    'memberships': memberships,
    'purchased_courses_count': purchased_courses_count,
    'completed_courses_count': completed_courses_count,

    })





def certificate_view(request, level_name):
    # Fetch user information
    user = request.user
    first_name = user.first_name
    last_name = user.last_name

    # Pass data to the template
    context = {
        'level_name': level_name,
        'first_name': first_name,
        'last_name': last_name,
    }
    return render(request, 'dashboard/certificate.html', context)