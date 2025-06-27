from django.contrib import admin
from .models import *

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'phone']
    search_fields = ['user__username', 'phone']

class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'seller', 'price', 'stock']
    list_filter = ['category', 'is_featured']

class DeliveryPersonAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'profile_picture', 'created_at']

class AddressAdmin(admin.ModelAdmin):
    list_display = ['customer', 'address_text', 'is_default']
    list_filter = ['is_default']
    search_fields = ['customer__name', 'address_text']

class SupercoinAdmin(admin.ModelAdmin):
    list_display = ['customer', 'amount', 'transaction_type', 'created_at']
    list_filter = ['transaction_type']
    search_fields = ['customer__name']

admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(Category)
admin.site.register(Customer)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Payment)
admin.site.register(Review)
admin.site.register(DeliveryPerson, DeliveryPersonAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(Supercoin, SupercoinAdmin)