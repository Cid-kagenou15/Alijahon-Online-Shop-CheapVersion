import re
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.forms import Form, ModelForm
from django.forms.fields import CharField
from myapp.models import Product, Stream, Withdraw
from myapp.models import User, District, Order

class AuthForm(Form):
    phone_number = CharField(max_length=50)
    password = CharField(max_length=10)

    def clean_password(self):
        password = self.cleaned_data.get('password')
        return make_password(password)

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        digits_only = re.sub(r"\D", "", phone_number)  # Remove all non-digit characters
        if not digits_only.startswith("998"):  # Ensure it follows Uzbekistan's country code
            digits_only = "998" + digits_only.lstrip("998")
        return f"+{digits_only}"

    def save(self):
        phone_number = self.cleaned_data.get("phone_number")
        password = make_password(self.cleaned_data.get("password"))  # Hash password
        obj, _ = User.objects.get_or_create(phone_number=phone_number, defaults={"password": password})
        return obj

class RegisterForm(UserCreationForm):
    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        digits_only = re.sub(r"\D", "", phone_number)
        if not digits_only.startswith("998"):
            digits_only = "998" + digits_only.lstrip("998")
        return f"+{digits_only}"

    class Meta:
        model = User
        fields = ["phone_number", "password1", "password2"]

class ProfileForm(forms.Form):
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)
    district_id = forms.IntegerField(required=False)  # Ensure it expects an integer
    address = forms.CharField(required=False)
    telegram_id = forms.IntegerField(required=False, min_value=1)  # Accepts empty but prevents negative numbers
    about = forms.CharField(required=False)

    def update(self, user):
        data = self.cleaned_data

        # Update fields
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        user.address = data.get('address', user.address)
        user.about = data.get('about', user.about)

        # Handle Telegram ID correctly
        telegram_id = data.get('telegram_id')
        if telegram_id:
            user.telegram_id = telegram_id  # Assign only if valid

        # Handle District correctly
        district_id = data.get('district_id')
        if district_id:
            try:
                user.district = District.objects.get(id=district_id)
            except District.DoesNotExist:
                pass

        user.save()

class ChangePasswordForm(forms.Form):
    old = forms.CharField(widget=forms.PasswordInput, required=True)
    new = forms.CharField(widget=forms.PasswordInput, required=True)
    confirm = forms.CharField(widget=forms.PasswordInput, required=True)

    def clean_confirm(self):
        new = self.cleaned_data.get('new')
        confirm = self.cleaned_data.get('confirm')
        if new != confirm:
            raise ValidationError("New passwords do not match!")
        return confirm  # Always return the cleaned data

    def update(self, user):
        password = self.cleaned_data.get('new')
        user.set_password(password)  # Securely set the new password
        user.save()  # Save the user with the new hashed password

class OrderForm(forms.Form):
    last_name = forms.CharField(max_length=255)
    phone_number = forms.CharField(max_length=20)
    product_id = forms.IntegerField(widget=forms.HiddenInput())
    quantity = forms.IntegerField(min_value=1, initial=1)
    stream = forms.ModelChoiceField(queryset=Stream.objects.all(),
                                    required=False)  # Correctly add ModelChoiceField for stream

    def __init__(self, *args, **kwargs):
        # Get the product ID from kwargs and pass it to the form
        product_id = kwargs.pop('product_id', None)
        super().__init__(*args, **kwargs)
        if product_id:
            self.fields['product_id'].initial = product_id

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        # Remove non-digit characters but keep the '+' sign at the start
        digits_only = "+" + re.sub(r"\D", "", phone_number)
        return digits_only

    def save(self, user, stream=None):
        # Retrieve the product using the product ID in the form
        product = Product.objects.get(id=self.cleaned_data["product_id"])

        # If the form has a stream, use it, otherwise use the provided stream argument
        stream = stream or self.cleaned_data.get('stream')

        # Create and save the order with or without a stream
        order = Order.objects.create(
            owner=user,
            product=product,
            last_name=self.cleaned_data["last_name"],
            phone_number=self.cleaned_data["phone_number"],
            quantity=self.cleaned_data["quantity"],
            stream=stream  # Ensure the stream is passed here
        )

        order.amount = order.amount_summa
        order.save()

        return order

class StreamForm(forms.ModelForm):
    class Meta:
        model = Stream
        fields = ['name', 'discount_sum']

class WithdrawForm(ModelForm):
    class Meta:
        model = Withdraw
        fields = ['amount', 'payment_method']
        labels = {
            'amount': 'Miqdor (so‘m)',
            'payment_method': 'To‘lov usuli',
        }

class OperatorForm(Form):
    category_id = CharField(required=False)
    district_id = CharField(required=False)

class OrderModelForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['comment_operator'].required = False

    class Meta:
        model = Order
        fields = ['quantity', 'send_date', 'district', 'status', 'comment_operator']