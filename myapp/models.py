from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractUser, UserManager
from django.db.models import Model, CharField, ForeignKey, DecimalField, ImageField, DateTimeField, CASCADE, TextField, \
    IntegerField, SET_NULL, BigIntegerField, TextChoices, SlugField, SmallIntegerField
from django.utils.text import slugify
from django.db import models
from decimal import Decimal

from root import settings

class CustomUserManager(UserManager):
    def _create_user(self, phone_number, password, **extra_fields):

        if not phone_number:
            raise ValueError("The given phone number must be set")

        user = self.model(phone_number=phone_number, **extra_fields)
        user.password = make_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(phone_number, password, **extra_fields)

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(phone_number, password, **extra_fields)

class User(AbstractUser):
    class RoleType(TextChoices):
        ADMIN = 'admin', 'Admin'
        USER = 'user', 'User'
        OPERATOR = 'operator', 'Operator'

    objects = CustomUserManager()
    USERNAME_FIELD = 'phone_number'
    username = None
    phone_number = CharField(max_length=20, unique=True)
    district = ForeignKey('myapp.District', on_delete=SET_NULL, null=True, blank=True)
    address = TextField()
    telegram_id = BigIntegerField(unique=True, blank=True, null=True)
    about = TextField(blank=True, null=True)
    role = CharField(max_length=10, choices=RoleType, default=RoleType.USER)
    balance = DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Balans")

class BaseSlugModel(Model):
    name = CharField(max_length=255)
    slug = SlugField(max_length=255, unique=True, blank=True, null=True)

    class Meta:
        abstract = True

    def save(self, **kwargs):
        slug = slugify(self.name)
        i = 1
        while Category.objects.filter(slug=slug).exists():
            slug += f"-{i}"
            i += 1
        self.slug = slug
        super().save()

class Region(Model):
    name = CharField(max_length=255)

class District(Model):
    name = CharField(max_length=255)
    region = ForeignKey('myapp.Region', on_delete=CASCADE)

class Category(BaseSlugModel):
    icon = CharField(max_length=255)

    def __str__(self):
        return self.name

class Product(BaseSlugModel):
    description = TextField()
    price = DecimalField(max_digits=10, decimal_places=2)
    image = ImageField(upload_to='products/')
    category = ForeignKey('myapp.Category', on_delete=CASCADE)
    sell_price = DecimalField(max_digits=10, decimal_places=0)
    quantity = SmallIntegerField(default=1)
    sale = CharField(max_length=50, default=None, null=True, blank=True)
    telegram_url = CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.name

class Wishlist(Model):
    user = ForeignKey(User, on_delete=CASCADE)
    product = ForeignKey('myapp.Product', on_delete=CASCADE)

class Order(models.Model):
    class StatusType(TextChoices):
        NEW = 'new', 'New'
        PENDING = 'pending', 'Pending'
        COMPLETED = 'completed', 'Completed'
        CANCELED = 'canceled', 'Canceled'
        READY_TO_ORDER = 'ready_to_order', 'Ready To Order'
        DELIVERING = 'delivering', 'Delivering'
        DELIVERED = 'delivered', 'Delivered'
        ARCHIVED = 'archived', 'Archived'
        NOT_PICK_UP = 'not_pick_up', 'Not Pick Up'

    last_name = CharField(max_length=255)
    owner = ForeignKey('myapp.User', on_delete=SET_NULL, null=True, blank=True, related_name='orders')
    phone_number = CharField(max_length=20)
    ordered_at = DateTimeField(auto_now_add=True)
    stream = ForeignKey('myapp.Stream', on_delete=SET_NULL, null=True, related_name='orders')
    product = ForeignKey('myapp.Product', on_delete=CASCADE, related_name='orders')
    quantity = IntegerField(default=1)
    status = CharField(max_length=20, choices=StatusType, default=StatusType.NEW)
    amount = DecimalField(max_digits=10, decimal_places=0, default=0, null=True, blank=True)

    send_date = DateTimeField(null=True, blank=True)
    district = ForeignKey('District', on_delete=SET_NULL, null=True, blank=True)
    comment_operator = TextField(blank=True, null=True)

    @property
    def amount_summa(self):
        """Calculate the total product cost before delivery."""
        return self.quantity * self.product.price if self.product else Decimal(0)

    @property
    def delivery_price(self):
        """Fetch the delivery fee from AdminSetting (returns 0 if no setting)."""
        admin_setting = AdminSetting.objects.first()
        return admin_setting.deliver_price if admin_setting else Decimal(0)

    @property
    def total_price(self):
        """Calculate the full order price including delivery."""
        return self.amount_summa + self.delivery_price

    def __str__(self):
        return f"Order #{self.id} - {self.status} by {self.owner.username if self.owner else 'Guest'}"

    class Meta:
        ordering = ['-ordered_at']  # Show newest orders first

class Stream(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey('myapp.Product', on_delete=models.CASCADE)  # Corrected ForeignKey syntax
    discount_sum = models.DecimalField(max_digits=10, decimal_places=2)  # Fixed to DecimalField
    name = models.CharField(max_length=255)  # Corrected to CharField
    created_at = models.DateTimeField(auto_now_add=True)
    visit_count = models.IntegerField(default=0)

    def __str__(self):
        return self.name

class Payment(Model):
    class StatusType(TextChoices):
        REVIEW = 'review', 'Review'
        COMPLETED = 'completed', 'Completed'
        CANCEL = 'cancel', 'Cancel'

    user = ForeignKey('myapp.User', on_delete=CASCADE)
    amount = DecimalField(max_digits=10, decimal_places=2)
    photo = ImageField(upload_to='payment/')
    payment_at = DateTimeField(auto_now_add=True)
    status = CharField(max_length=10, choices=StatusType , default=StatusType.REVIEW)
    description = TextField(blank=True, null=True)

class AdminSetting(models.Model):
    deliver_price = models.DecimalField(
        max_digits=6, decimal_places=0, default=0,
        help_text="Delivery price in whole numbers."
    )
    competition_photo = models.ImageField(
        upload_to='admin/%Y/%m/', null=True, blank=True,
        help_text="Upload an image related to the competition."
    )
    start = models.DateField(default='2024-09-20')
    finish = models.DateField(default='2025-03-20')
    description = models.TextField(blank=True, null=True, help_text="Optional competition details.")

    class Meta:
        verbose_name = "Admin Setting"
        verbose_name_plural = "Admin Settings"

    def __str__(self):
        return f"Competition ({self.start} - {self.finish})"

class Withdraw(Model):
    user = ForeignKey(settings.AUTH_USER_MODEL, on_delete=CASCADE, related_name='withdraws')
    amount = DecimalField(max_digits=15, decimal_places=2, verbose_name="Miqdor (so‘m)")
    payment_method = CharField(
        max_length=20,
        choices=[('card', 'Karta'), ('cash', 'Naqd')],
        verbose_name="To‘lov usuli"
    )
    status = CharField(
        max_length=20,
        choices=[('pending', 'Kutilmoqda'), ('approved', 'Tasdiqlangan'), ('rejected', 'Rad etilgan')],
        default='pending',
        verbose_name="Holati"
    )
    created_at = DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqt")

    def __str__(self):
        return f"{self.user} - {self.amount} so‘m - {self.status}"

    class Meta:
        verbose_name = "To‘lov so‘rovi"
        verbose_name_plural = "To‘lov so‘rovlari"