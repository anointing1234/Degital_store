from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={
        'class': 'form-control col-12 mb-3',
        'aria-label': 'Email Address'
    }))
    
    first_name = forms.CharField(required=True, widget=forms.TextInput(attrs={
        'class': 'form-control col-12 mb-3',
        'aria-label': 'First Name'
    }))
    
    last_name = forms.CharField(required=True, widget=forms.TextInput(attrs={
        'class': 'form-control col-12 mb-3',
        'aria-label': 'Last Name'
    }))

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control form-control-bg col-12 mb-3',
            }),
            'password1': forms.PasswordInput(attrs={
                'class': 'form-control form-control-bg col-12 mb-3',
            }),
            'password2': forms.PasswordInput(attrs={
                'class': 'form-control form-control-bg col-12 mb-3',
            }),
        }

    def __init__(self, *args, **kwargs):
        super(RegisterForm, self).__init__(*args, **kwargs)
        # Remove help text
        for field in self.fields.values():
            field.help_text = None



    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('A user with this email already exists.')
        return email


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'class': 'form-control form-control-bg col-12 mb-3',  # Changed mb-5 to mb-3 for consistency
        'placeholder': 'Username',
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control form-control-bg col-12 mb-3',  # Changed mb-5 to mb-3 for consistency
        'placeholder': 'Password',
    }))

    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        # Remove help text
        for field in self.fields.values():
            field.help_text = None
            
            
            
            
class PasswordResetForm(forms.Form):
    email = forms.EmailField(
        label="Enter your email address",
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'form-control border-none',  # Bootstrap class for styling
            'placeholder': 'example@example.com',
            'style': 'border: 1px solid black;',  # Placeholder text
        }),
        error_messages={
            'required': 'This field is required.',
            'invalid': 'Enter a valid email address.',
        }
    )  
 
 
class PasswordResetConfirmForm(forms.Form):
    reset_code = forms.CharField(
        max_length=6,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your reset code',
            'style': 'border: 1px solid black;'
        }),
        label="Reset Code"
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your new password',
            'style': 'border: 1px solid black;'
        }),
        label="New Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm your new password',
            'style': 'border: 1px solid black;'
        }),
        label="Confirm Password"
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError("New password and confirm password do not match.")
        return cleaned_data

              