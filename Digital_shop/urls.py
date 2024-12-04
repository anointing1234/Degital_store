from django.urls import path, re_path
from . import views
from django.conf.urls.static import static
from django.conf import settings
from django.conf.urls import handler404, handler500
from django.views.static import serve 





urlpatterns = [
    path('', views.home, name='index'),
    path('pay_master/',views.pay_master,name='pay_master'),
    path('home/', views.home, name='home'),
    path('create-checkout-session/<int:pk>/', views.CreateStripeCheckoutSessionView.as_view(), name='create-checkout-session'),
    path('create-paystack-transaction/<int:pk>/', views.CreatePaystackTransactionView.as_view(), name='create-paystack-transaction'),
    path('stripe_membership_payment/<int:pk>/<str:level>/',views.StripeMembershipCheckoutSession.as_view(),name='stripe_membership_payment'),
    path('paystack_membership_payment/<int:pk>/<str:level>/',views.PaystackMembershipcheckoutSession.as_view(),name='paystack_membership_payment'),
    path('success_stripe_membership/',views.success_stripe_membership,name='success_stripe_membership'),
    path('paystack_membership/success/',views.paystack_membership,name='paystack_membership'),
    path('paystack/success/', views.paystack_success, name='paystack-success'),
    path('paystack_success/success/',views.paystack_success2,name='paystack_success2'),
    path('success/', views.payment_success, name='payment_success'),
    path('success_stripe/',views.payment__stripe_success,name='success_stripe'),
    path('library/', views.library, name='library'),
    path('login/', views.login, name='login'),  # Added trailing slash
    path('signup/', views.register, name='signup'),
    path('register/', views.register_view, name='register'),
    path('Login/', views.login_view, name='Login'),
    path('logout/', views.custom_logout_view, name='logout'),
    path('handle-payment/<int:product_id>/', views.handle_payment, name='handle-payment'),
    path('send_password_reset/',views.sendpasswordresetmail,name='send_password_reset'),
    path('password-reset/',views.request_password_reset, name='request_password_reset'),
    path('reset_password_page/',views.reset_password_page,name='reset_password_page'),
    path('comfirm_password/',views.confirm_password_reset,name='comfirm_password'),
    path('cart/',views.cart,name='cart'),
    path('cart/remove/<int:item_id>/',views.remove_cart_item, name='remove_cart_item'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('handle-item-payment/',views.handle_item_payment, name='handle-item-payment'),
    path('create-checkout-sessions/<str:product_ids>/', views.CreateStripeCheckoutSessionsView.as_view(), name='create-checkout-sessions'),
    path('create-paystack-transactions/<str:product_ids>/', views.CreatePaystackTransactionsView.as_view(), name='create-paystack-transactions'),
    path('cancel/',views.cancel,name='cancel'),
    path('training/',views.training_view,name='training'),
    path('membership_payment/',views.membership_payment,name='membership_payment'),
    path('dashboard/',views.dashboard,name="dashboard"),
    re_path(r'^media/(?P<path>.*)$', serve,{'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve,{'document_root': settings.STATIC_ROOT}),
    
] + static(settings.STATIC_URL,document_root=settings.STATIC_ROOT)

handler404 = views.custom_404_view
handler500 = views.custom_500_view