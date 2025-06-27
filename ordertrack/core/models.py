from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.db.models import Sum, F
from decimal import Decimal
from django.db.models import Avg, Count
import os

class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('buyer', 'Buyer'),
        ('seller', 'Seller'),
        ('delivery', 'Delivery Person'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    phone = models.CharField(max_length=20, blank=True)
    bio = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"
    
    @property
    def is_seller(self):
        return self.role == 'seller'
    
    @property
    def is_buyer(self):
        return self.role == 'buyer'
    
    @property
    def is_delivery(self):
        return self.role == 'delivery'

class DeliveryPerson(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='delivery_profile')
    phone_number = models.CharField(max_length=15, default='00000000')  # remove unique=True
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    # Add these if you want:
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        try:
            this = DeliveryPerson.objects.get(pk=self.pk)
            if this.profile_picture and self.profile_picture != this.profile_picture:
                if os.path.isfile(this.profile_picture.path):
                    os.remove(this.profile_picture.path)
        except DeliveryPerson.DoesNotExist:
            pass  # New object, no old file to remove
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.profile_picture and os.path.isfile(self.profile_picture.path):
            os.remove(self.profile_picture.path)
        super().delete(*args, **kwargs)

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='category_images/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Product(models.Model):
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='product_images/')
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    discount_percent = models.PositiveIntegerField(default=0, help_text="Discount percentage (0-100)")
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    @property
    def available(self):
        return self.stock > 0
    
    @property
    def discounted_price(self):
        if self.discount_percent and self.discount_percent > 0:
            discount = Decimal(self.discount_percent) / Decimal('100')
            return self.price * (Decimal('1') - discount)
        return self.price

    def reduce_stock(self, quantity):
        """Reduce product stock by given quantity"""
        if quantity > self.stock:
            raise ValueError("Insufficient stock")
        self.stock -= quantity
        self.save()
    
    def increase_stock(self, quantity):
        """Increase product stock by given quantity"""
        self.stock += quantity
        self.save()

    @property
    def average_rating(self):
        """Calculate average rating for the product"""
        avg = self.reviews.aggregate(avg_rating=Avg('rating'))['avg_rating']
        return round(avg, 1) if avg else 0.0

    @property
    def rating_breakdown(self):
        """Calculate percentage of each rating (1-5 stars)"""
        total_reviews = self.reviews.count()
        if total_reviews == 0:
            return {i: 0 for i in range(1, 6)}
        breakdown = self.reviews.values('rating').annotate(count=Count('rating'))
        percentages = {i: 0 for i in range(1, 6)}
        for entry in breakdown:
            percentages[entry['rating']] = round((entry['count'] / total_reviews) * 100)
        return percentages

class Address(models.Model):
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='addresses')
    address_text = models.TextField()
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer.name}'s address: {self.address_text[:50]}..."

    def save(self, *args, **kwargs):
        if self.is_default:
            # Ensure only one default address per customer
            Address.objects.filter(customer=self.customer, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer')
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField()
    shipping_address = models.TextField(blank=True, null=True)
    billing_address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def get_default_shipping_address(self):
        default_address = self.addresses.filter(is_default=True).first()
        return default_address.address_text if default_address else (self.shipping_address or self.address)
    
    def get_default_billing_address(self):
        return self.billing_address or self.address

class Supercoin(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='supercoins')
    amount = models.PositiveIntegerField(default=0)
    transaction_type = models.CharField(max_length=20, choices=[
        ('earned', 'Earned'),
        ('redeemed', 'Redeemed')
    ])
    order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='supercoin_transactions')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.customer.name} - {self.amount} Supercoins ({self.transaction_type})"

    @property
    def total_balance(self):
        """Calculate total Supercoin balance for the customer"""
        earned = self.customer.supercoins.filter(transaction_type='earned').aggregate(total=Sum('amount'))['total'] or 0
        redeemed = self.customer.supercoins.filter(transaction_type='redeemed').aggregate(total=Sum('amount'))['total'] or 0
        return earned - redeemed

class Order(models.Model):
    PENDING = 'pending'
    PROCESSING = 'processing'
    SHIPPED = 'shipped'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (PROCESSING, 'Processing'),
        (SHIPPED, 'Shipped'),
        (DELIVERED, 'Delivered'),
        (CANCELLED, 'Cancelled'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
    delivery_person = models.ForeignKey(DeliveryPerson, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    address = models.ForeignKey(Address, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    shipping_address = models.TextField(blank=True, null=True)
    billing_address = models.TextField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    has_spun = models.BooleanField(default=False)  # Add this field
    spin_prize = models.PositiveIntegerField(default=0)  # Optionally store the prize
    supercoins_used = models.PositiveIntegerField(default=0)
    supercoin_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} - {self.customer.name}"

    @property
    def total_price(self):
        """Calculate total price of all order items"""
        total = self.items.aggregate(
            total=Sum(F('quantity') * F('price'))
        )['total']
        return total or 0

    @property
    def item_count(self):
        """Count of items in this order"""
        return self.items.count()

    def can_cancel(self):
        """Check if order can be cancelled"""
        return self.status in [self.PENDING, self.PROCESSING]

    def mark_as_shipped(self):
        """Mark order as shipped"""
        if self.status != self.PROCESSING:
            raise ValueError("Only processing orders can be shipped")
        self.status = self.SHIPPED
        self.save()

    def mark_as_delivered(self):
        """Mark order as delivered"""
        if self.status != self.SHIPPED:
            raise ValueError("Only shipped orders can be delivered")
        self.status = self.DELIVERED
        self.save()

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    price = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name} (Order #{self.order.id})"
    
    @property
    def total_price(self):
        return self.quantity * self.price
    
    def save(self, *args, **kwargs):
        """Set price from product price when saving"""
        if not self.price:
            self.price = self.product.price
        super().save(*args, **kwargs)

class Payment(models.Model):
    PENDING = 'pending'
    COMPLETED = 'completed'
    FAILED = 'failed'
    REFUNDED = 'refunded'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (COMPLETED, 'Completed'),
        (FAILED, 'Failed'),
        (REFUNDED, 'Refunded'),
    ]
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    supercoins_used = models.PositiveIntegerField(default=0)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    payment_method = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Payment for Order #{self.order.id}"
    
    def mark_as_completed(self, transaction_id=None):
        """Mark payment as completed"""
        self.status = self.COMPLETED
        self.transaction_id = transaction_id
        self.payment_date = timezone.now()
        self.save()
        
        if self.order.status == Order.PENDING:
            self.order.status = Order.PROCESSING
            self.order.save()
    
    def mark_as_failed(self):
        """Mark payment as failed"""
        self.status = self.FAILED
        self.save()
    
    def issue_refund(self):
        """Issue refund for this payment"""
        if self.status != self.COMPLETED:
            raise ValueError("Only completed payments can be refunded")
        self.status = self.REFUNDED
        self.save()
        
        if self.order.can_cancel():
            self.order.status = Order.CANCELLED
            self.order.save()
        
        # Refund Supercoins if used
        if self.supercoins_used > 0:
            Supercoin.objects.create(
                customer=self.order.customer,
                amount=self.supercoins_used,
                transaction_type='earned',
                order=self.order
            )

class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('product', 'customer')
    
    def __str__(self):
        return f"{self.rating} stars for {self.product.name} by {self.customer.name}"

class Wishlist(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='wishlist')
    products = models.ManyToManyField(Product, related_name='wishlisted_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Wishlist of {self.customer.name}"
    
    def add_product(self, product):
        """Add product to wishlist"""
        self.products.add(product)
    
    def remove_product(self, product):
        """Remove product from wishlist"""
        self.products.remove(product)
    
    def clear(self):
        """Clear all products from wishlist"""
        self.products.clear()

