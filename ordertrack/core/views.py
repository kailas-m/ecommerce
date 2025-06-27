from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from .forms import BuyerRegistrationForm, SellerRegistrationForm, ProductForm, OrderForm, CustomerForm, CategoryForm, DeliveryPersonRegistrationForm, DeliveryPersonForm, SellerProfileForm, AddressForm
from .models import Product, Category, Order, UserProfile, Customer, OrderItem, Wishlist, DeliveryPerson, Payment, Review, Address, Supercoin
from django.db.models import Sum, F, Avg, ExpressionWrapper, DecimalField
from django.urls import reverse
from django.db import transaction
from django.db.models import Prefetch
from django.contrib.auth.models import User
import random
from django.views.decorators.http import require_POST
from .models import DeliveryPerson
import os
from django.core.mail import send_mail
from django.conf import settings

def index(request):
    categories = Category.objects.filter(is_active=True)
    featured_products = Product.objects.filter(is_featured=True, is_active=True)[:4]
    wishlist_product_ids = []
    wishlist_count = 0
    if request.user.is_authenticated and hasattr(request.user, "profile") and request.user.profile.role == "buyer":
        customer = Customer.objects.get(user=request.user)
        wishlist, _ = Wishlist.objects.get_or_create(customer=customer)
        wishlist_product_ids = list(wishlist.products.values_list('id', flat=True))
        wishlist_count = wishlist.products.count()
    context = {
        'categories': categories,
        'featured_products': featured_products,
        "wishlist_product_ids": wishlist_product_ids,
        "wishlist_count": wishlist_count,
        "wishlist_products": wishlist.products.all() if request.user.is_authenticated and hasattr(request.user, "profile") and request.user.profile.role == "buyer" else [],
    }
    return render(request, "index.html", context)

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            try:
                profile = user.profile
                role = profile.role.lower().strip()
                print(f"✅ User logged in: {username}, role: {role}")
                if role == 'seller':
                    return redirect('seller_dashboard')
                elif role == 'buyer':
                    return redirect('customer_dashboard')
                elif role == 'delivery':
                    return redirect('delivery_dashboard')
                else:
                    messages.warning(request, "Unknown user role.")
                    return redirect('index')
            except Exception as e:
                print(f"❌ Error accessing user profile: {e}")
                messages.error(request, "User profile not found.")
                return redirect('login')
        else:
            print("❌ Invalid credentials")
            messages.error(request, 'Invalid username or password')
    return render(request, 'login.html')

def login_buyer(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.profile.is_buyer:
            login(request, user)
            return redirect('customer_dashboard')
        else:
            messages.error(request, 'Invalid credentials or not a buyer account.')
    return render(request, 'auth/login_buyer.html')

def login_seller(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.profile.is_seller:
            login(request, user)
            return redirect('seller_dashboard')
        else:
            messages.error(request, 'Invalid credentials or not a seller account.')
    return render(request, 'auth/login_seller.html')

def login_delivery(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None and user.profile.is_delivery:
            login(request, user)
            return redirect('delivery_dashboard')
        else:
            messages.error(request, 'Invalid credentials or not a delivery person account.')
    return render(request, 'auth/login_delivery.html')

def logout_view(request):
    logout(request)
    return redirect('index')

@transaction.atomic
def register_buyer(request):
    if request.method == 'POST':
        form = BuyerRegistrationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password'])
                user.save()
                profile, created = UserProfile.objects.get_or_create(user=user, defaults={'role': 'buyer'})
                profile.role = 'buyer'
                profile.save()
                customer, created = Customer.objects.get_or_create(
                    user=user,
                    defaults={
                        'name': form.cleaned_data['username'],
                        'email': form.cleaned_data['email'],
                        'address': ''
                    }
                )
                if customer.address:
                    Address.objects.create(
                        customer=customer,
                        address_text=customer.address,
                        is_default=True
                    )
                print(f"✅ Created customer for {user.username}: {customer}")
            messages.success(request, 'Buyer account created successfully! Please login.')
            return redirect('login_buyer')
    else:
        form = BuyerRegistrationForm()
    return render(request, 'auth/register_buyer.html', {'form': form, 'user_type': 'buyer'})

def register_seller(request):
    if request.method == 'POST':
        form = SellerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            profile, created = UserProfile.objects.get_or_create(user=user, defaults={'role': 'seller'})
            profile.role = 'seller'
            profile.save()
            messages.success(request, 'Seller account created successfully! Please login.')
            return redirect('login_seller')
    else:
        form = SellerRegistrationForm()
    return render(request, 'auth/register_seller.html', {'form': form, 'user_type': 'seller'})

@transaction.atomic
def register_delivery(request):
    if request.method == 'POST':
        user_form = DeliveryPersonRegistrationForm(request.POST)
        delivery_form = DeliveryPersonForm(request.POST, request.FILES)  # <-- Add request.FILES
        if user_form.is_valid() and delivery_form.is_valid():
            with transaction.atomic():
                user = user_form.save(commit=False)
                user.set_password(user_form.cleaned_data['password'])
                user.save()
                profile, created = UserProfile.objects.get_or_create(user=user, defaults={'role': 'delivery'})
                profile.role = 'delivery'
                profile.save()
                delivery_person = delivery_form.save(commit=False)
                delivery_person.user = user
                delivery_person.save()
                messages.success(request, 'Delivery person account created successfully! Please login.')
                return redirect('login_delivery')
    else:
        user_form = DeliveryPersonRegistrationForm()
        delivery_form = DeliveryPersonForm()
    return render(request, 'auth/register_delivery.html', {'user_form': user_form, 'delivery_form': delivery_form, 'user_type': 'delivery'})

def product_list(request):
    products = Product.objects.filter(is_active=True)
    category_id = request.GET.get('category')
    seller_id = request.GET.get('seller')
    if category_id:
        products = products.filter(category_id=category_id)
    if seller_id:
        products = products.filter(seller_id=seller_id)
    q = request.GET.get('q')
    if q:
        products = products.filter(name__icontains=q)
    sort = request.GET.get('sort')

    products = products.annotate(
        discounted_price_ann=ExpressionWrapper(
            F('price') * (1 - F('discount_percent') / 100.0),
            output_field=DecimalField(max_digits=10, decimal_places=2)
        )
    )

    if sort == 'price_asc':
        products = products.order_by('discounted_price_ann')
    elif sort == 'price_desc':
        products = products.order_by('-discounted_price_ann')
    elif sort == 'rating_desc':
        products = products.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')
    elif sort == 'rating_asc':
        products = products.annotate(avg_rating=Avg('reviews__rating')).order_by('avg_rating')
    elif sort == 'name_asc':
        products = products.order_by('name')
    elif sort == 'name_desc':
        products = products.order_by('-name')

    sellers = User.objects.filter(products__is_active=True, profile__role='seller').distinct()

    wishlist_product_ids = []
    wishlist_count = 0
    if request.user.is_authenticated and hasattr(request.user, "profile") and request.user.profile.role == "buyer":
        customer = Customer.objects.get(user=request.user)
        wishlist, _ = Wishlist.objects.get_or_create(customer=customer)
        wishlist_product_ids = list(wishlist.products.values_list('id', flat=True))
        wishlist_count = wishlist.products.count()

    context = {
        'products': products,
        'categories': Category.objects.filter(is_active=True),
        'sellers': sellers,
        "wishlist_product_ids": wishlist_product_ids,
        "wishlist_count": wishlist_count,
    }
    return render(request, "product_list.html", context)

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    reviews = product.reviews.order_by('-created_at')  # Get all reviews for this product
    return render(request, 'product_detail.html', {
        'product': product,
        'reviews': reviews,
        'categories': Category.objects.filter(is_active=True)
    })

@login_required
def seller_dashboard(request):
    if not request.user.profile.is_seller:
        messages.error(request, 'Access denied. Seller account required.')
        return redirect('index')
    products = Product.objects.filter(seller=request.user, is_active=True)
    total_products = products.count()
    out_of_stock = products.filter(stock=0).count()
    total_sales = OrderItem.objects.filter(product__seller=request.user).aggregate(
        total=Sum(F('quantity') * F('price'))
    )['total'] or 0
    context = {
        'products': products,
        'total_products': total_products,
        'out_of_stock': out_of_stock,
        'total_sales': total_sales,
        'categories': Category.objects.filter(is_active=True)
    }
    return render(request, 'seller_dashboard.html', context)

@login_required
def customer_dashboard(request):
    if not request.user.profile.is_buyer:
        messages.error(request, 'Access denied. Buyer account required.')
        return redirect('index')
    try:
        customer = Customer.objects.get(user=request.user)
    except Customer.DoesNotExist:
        messages.error(request, 'Customer profile not found. Please contact support.')
        return redirect('index')
    orders = Order.objects.filter(customer=customer).order_by('-created_at')
    wishlist = Wishlist.objects.get_or_create(customer=customer)[0]
    supercoin_balance = Supercoin.objects.filter(customer=customer).first().total_balance if Supercoin.objects.filter(customer=customer).exists() else 0
    context = {
        'orders': orders,
        'wishlist': wishlist.products.all(),
        'customer': customer,
        'categories': Category.objects.filter(is_active=True),
        'supercoin_balance': supercoin_balance,
    }
    return render(request, 'customer_dashboard.html', context)

@login_required
def delivery_dashboard(request):
    if not request.user.profile.is_delivery:
        messages.error(request, 'Access denied.')
        return redirect('index')
    delivery_person = get_object_or_404(DeliveryPerson, user=request.user)
    all_orders = Order.objects.all().order_by('-created_at')
    if request.method == 'POST':
        order_id = request.POST.get('order_id')
        action = request.POST.get('action')
        order = get_object_or_404(Order, id=order_id)
        if action == 'accept':
            if order.delivery_person is None:
                order.delivery_person = delivery_person
                order.save()
                messages.success(request, f'You have accepted order #{order.id}.')
            else:
                messages.error(request, 'Order already assigned.')
        elif action == 'complete':
            if order.delivery_person == delivery_person and order.status != 'delivered':
                payment = getattr(order, 'payment', None)
                if payment and payment.payment_method == 'cod' and payment.status != Payment.COMPLETED:
                    messages.error(request, 'You must confirm payment before marking this COD order as complete.')
                else:
                    order.status = 'delivered'
                    order.save()
                    messages.success(request, f'Order #{order.id} marked as completed.')
            else:
                messages.error(request, 'You cannot mark this order as complete.')
        elif action == 'confirm_payment':
            payment = getattr(order, 'payment', None)
            if payment and payment.payment_method == 'cod' and payment.status != Payment.COMPLETED:
                payment.status = Payment.COMPLETED
                payment.save()
                messages.success(request, f'Payment for order #{order.id} confirmed as received.')
            else:
                messages.error(request, 'Payment already confirmed or not COD.')
        return redirect('delivery_dashboard')
    return render(request, 'delivery_dashboard.html', {
        'orders': all_orders,
        'delivery_person': delivery_person,
        'categories': Category.objects.filter(is_active=True)
    })

@login_required
def delivery_pending(request):
    if not request.user.profile.is_delivery:
        messages.error(request, 'Access denied.')
        return redirect('index')
    delivery_person = get_object_or_404(DeliveryPerson, user=request.user)
    orders = Order.objects.filter(status__in=['pending', 'processing']).order_by('-created_at')
    return render(request, 'delivery_dashboard.html', {
        'orders': orders,
        'delivery_person': delivery_person,
        'categories': Category.objects.filter(is_active=True)
    })

@login_required
def delivery_completed(request):
    if not request.user.profile.is_delivery:
        messages.error(request, 'Access denied.')
        return redirect('index')
    delivery_person = get_object_or_404(DeliveryPerson, user=request.user)
    orders = Order.objects.filter(status='delivered', delivery_person=delivery_person).order_by('-created_at')
    return render(request, 'delivery_dashboard.html', {
        'orders': orders,
        'delivery_person': delivery_person,
        'categories': Category.objects.filter(is_active=True)
    })

@login_required
def delivery_profile(request):
    delivery_profile = get_object_or_404(DeliveryPerson, user=request.user)
    if request.method == 'POST':
        form = DeliveryPersonForm(request.POST, request.FILES, instance=delivery_profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('delivery_profile')
    else:
        form = DeliveryPersonForm(instance=delivery_profile)
    # Add your stats context as needed
    return render(request, 'delivery_profile.html', {
        'delivery_profile': delivery_profile,
        'form': form,
        'total_deliveries': ...,  # your logic here
        'avg_rating': ...,        # your logic here
    })

@login_required
def update_order_status(request, pk):
    if not request.user.profile.is_delivery:
        messages.error(request, 'Access denied. Delivery person account required.')
        return redirect('index')
    order = get_object_or_404(Order, pk=pk, delivery_person__user=request.user)
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in [Order.SHIPPED, Order.DELIVERED]:
            try:
                if status == Order.SHIPPED:
                    order.mark_as_shipped()
                    messages.success(request, 'Order marked as shipped.')
                elif status == Order.DELIVERED:
                    order.mark_as_delivered()
                    messages.success(request, 'Order marked as delivered.')
                return redirect('delivery_dashboard')
            except ValueError as e:
                messages.error(request, str(e))
        else:
            messages.error(request, 'Invalid status update.')
    return render(request, 'update_order_status.html', {'order': order, 'categories': Category.objects.filter(is_active=True)})

@login_required
def product_create(request):
    if not request.user.profile.is_seller:
        messages.error(request, 'Access denied.')
        return redirect('index')
    if request.method == 'POST':
        form = ProductForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = request.user
            product.save()
            messages.success(request, 'Product created successfully!')
            return redirect('seller_dashboard')
    else:
        form = ProductForm(request.user)
    return render(request, 'product_create.html', {'form': form, 'categories': Category.objects.filter(is_active=True)})

@login_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk, seller=request.user)
    if request.method == 'POST':
        form = ProductForm(request.user, request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully!')
            return redirect('seller_dashboard')
    else:
        form = ProductForm(request.user, instance=product)
    return render(request, 'edit_product.html', {'form': form, 'product': product, 'categories': Category.objects.filter(is_active=True)})

@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk, seller=request.user)
    if request.method == 'POST':
        product.is_active = False
        product.save()
        messages.success(request, 'Product deleted successfully.')
        return redirect('seller_dashboard')
    return render(request, 'delete_product.html', {'product': product, 'categories': Category.objects.filter(is_active=True)})

@login_required
def create_order(request):
    if not request.user.profile.is_buyer:
        messages.error(request, 'Access denied. Buyer account required.')
        return redirect('index')
    try:
        customer = Customer.objects.get(user=request.user)
    except Customer.DoesNotExist:
        messages.error(request, 'Customer profile not found. Please complete your profile.')
        print(f"❌ No Customer object found for user: {request.user.username}")
        try:
            customer, created = Customer.objects.get_or_create(
                user=request.user,
                defaults={
                    'name': request.user.username,
                    'email': request.user.email or f"{request.user.username}@example.com",
                    'address': ''
                }
            )
            if created:
                print(f"✅ Created new Customer for {request.user.username}: {customer}")
            else:
                print(f"⚠️ Customer creation failed for {request.user.username}")
        except Exception as e:
            print(f"❌ Error creating Customer: {e}")
            return redirect('customer_profile')
    products = Product.objects.filter(is_active=True)
    if request.method == 'POST':
        order_form = OrderForm(request.POST)
        product_id = request.POST.get('product_id')
        quantity = request.POST.get('quantity', 1)
        if order_form.is_valid() and product_id and quantity:
            try:
                product = Product.objects.get(pk=product_id, is_active=True)
                if int(quantity) > product.stock:
                    messages.error(request, 'Requested quantity exceeds available stock.')
                    return redirect('product_detail', pk=product_id)
                order = order_form.save(commit=False)
                order.customer = customer
                order.shipping_address = customer.get_default_shipping_address()
                order.billing_address = customer.get_default_billing_address()
                order.save()
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=int(quantity),
                    price=product.discounted_price
                )
                product.reduce_stock(int(quantity))
                messages.success(request, 'Order placed successfully!')
                return redirect('cart')
            except Product.DoesNotExist:
                messages.error(request, 'Product not found.')
                return redirect('product_list')
        else:
            messages.error(request, 'Invalid order details.')
    else:
        order_form = OrderForm()
    return render(request, 'order_create.html', {
        'order_form': order_form,
        'item_form': {'product_id': request.GET.get('id'), 'quantity': 1},
        'products': products,
        'categories': Category.objects.filter(is_active=True)
    })

@login_required
def order_history(request):
    if not request.user.profile.is_buyer:
        messages.error(request, 'Access denied. Buyer account required.')
        return redirect('index')
    try:
        customer = Customer.objects.get(user=request.user)
    except Customer.DoesNotExist:
        messages.error(request, 'Customer profile not found. Please complete your profile.')
        return redirect('customer_profile')
    orders = Order.objects.filter(customer=customer).order_by('-created_at')
    return render(request, 'order_history.html', {'orders': orders, 'categories': Category.objects.filter(is_active=True)})

@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk)
    items_with_review_status = []
    if request.user.profile.is_buyer:
        customer = get_object_or_404(Customer, user=request.user)
        for item in order.items.all():
            existing_review = item.product.reviews.filter(customer=customer).first()
            items_with_review_status.append({
                'item': item,
                'has_review': bool(existing_review),
                'product_id': item.product.id
            })
    else:
        items_with_review_status = [{'item': item, 'has_review': False, 'product_id': item.product.id} for item in order.items.all()]
    
    return render(request, 'order_detail.html', {
        'order': order,
        'categories': Category.objects.filter(is_active=True),
        'items_with_review_status': items_with_review_status
    })

@login_required
def order_edit(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        form = OrderForm(request.POST, instance=order)
        payment_method = request.POST.get('payment_method')
        if form.is_valid() and payment_method:
            form.save()
            payment = Payment.objects.filter(order=order).first()
            if payment:
                payment.payment_method = payment_method
                payment.save()
            else:
                Payment.objects.create(
                    order=order,
                    amount=order.total_price,
                    payment_method=payment_method,
                    status=Payment.PENDING
                )
            messages.success(request, 'Order updated successfully!')
            return redirect('order_history')
    else:
        form = OrderForm(instance=order)
    return render(request, 'order_form.html', {'form': form, 'order': order, 'categories': Category.objects.filter(is_active=True)})

def order_list(request):
    orders = Order.objects.all().order_by('-created_at')
    return render(request, 'order_list.html', {'orders': orders, 'categories': Category.objects.filter(is_active=True)})

def category_list(request):
    categories = Category.objects.filter(is_active=True)
    return render(request, 'category_list.html', {'categories': categories})

@login_required
def category_add(request):
    if not request.user.profile.is_seller:
        messages.error(request, 'Access denied.')
        return redirect('index')
    if request.method == 'POST':
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category added successfully!')
            return redirect('category_list')
    else:
        form = CategoryForm()
    return render(request, 'category_add.html', {'form': form, 'categories': Category.objects.filter(is_active=True)})

@login_required
def wishlist_add(request, pk):
    if not request.user.profile.is_buyer:
        messages.error(request, 'Access denied. Buyer account required.')
        return redirect('index')
    customer = get_object_or_404(Customer, user=request.user)
    product = get_object_or_404(Product, pk=pk, is_active=True)
    wishlist, created = Wishlist.objects.get_or_create(customer=customer)
    wishlist.add_product(product)
    messages.success(request, 'Product added to wishlist!')
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('buyer_wishlist')

@login_required
def wishlist_remove(request, pk):
    if not request.user.profile.is_buyer:
        messages.error(request, 'Access denied.')
        return redirect('index')
    customer = get_object_or_404(Customer, user=request.user)
    product = get_object_or_404(Product, pk=pk)
    wishlist = get_object_or_404(Wishlist, customer=customer)
    wishlist.remove_product(product)
    messages.success(request, 'Product removed from wishlist.')
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('buyer_wishlist')

def customer_list(request):
    customers = Customer.objects.all()
    return render(request, 'customer_services.html', {'customers': customers, 'categories': Category.objects.filter(is_active=True)})

@login_required
def customer_profile(request):
    try:
        customer = Customer.objects.get(user=request.user)
    except Customer.DoesNotExist:
        customer = None
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.user = request.user
            customer.save()
            if customer.address:
                Address.objects.update_or_create(
                    customer=customer,
                    address_text=customer.address,
                    defaults={'is_default': not customer.addresses.exists()}
                )
            messages.success(request, 'Profile updated successfully!')
            return redirect('customer_profile')
    else:
        form = CustomerForm(instance=customer)
    supercoin_balance = Supercoin.objects.filter(customer=customer).first().total_balance if customer and Supercoin.objects.filter(customer=customer).exists() else 0
    return render(request, 'customer_profile.html', {
        'form': form,
        'address_form': AddressForm(),
        'categories': Category.objects.filter(is_active=True),
        'customer': customer,
        'supercoin_balance': supercoin_balance,
    })

@login_required
def add_to_cart(request, product_id):
    if not request.user.profile.is_buyer:
        messages.error(request, 'Access denied. Buyer account required.')
        return redirect('index')
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))
    if quantity > product.stock:
        messages.error(request, 'Requested quantity exceeds available stock.')
        return redirect('product_detail', pk=product_id)
    cart = request.session.get('cart', {})
    cart[str(product_id)] = cart.get(str(product_id), 0) + quantity
    request.session['cart'] = cart
    messages.success(request, 'Product added to cart!')
    return redirect('product_list')

@login_required
def cart(request):
    if not request.user.profile.is_buyer:
        messages.error(request, 'Access denied. Buyer account required.')
        return redirect('index')
    cart = request.session.get('cart', {})
    cart_items = []
    cart_total = 0
    for product_id, quantity in cart.items():
        product = get_object_or_404(Product, id=product_id)
        price = product.discounted_price
        subtotal = price * quantity
        cart_items.append({
            'product': product,
            'quantity': quantity,
            'subtotal': subtotal
        })
        cart_total += subtotal
    customer = get_object_or_404(Customer, user=request.user)
    supercoin_balance = Supercoin.objects.filter(customer=customer).first().total_balance if Supercoin.objects.filter(customer=customer).exists() else 0
    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'cart_total': cart_total,
        'categories': Category.objects.filter(is_active=True),
        'supercoin_balance': supercoin_balance,
    })

@login_required
def update_cart(request, product_id):
    if not request.user.profile.is_buyer:
        messages.error(request, 'Access denied. Buyer account required.')
        return redirect('index')
    cart = request.session.get('cart', {})
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))
    if quantity > product.stock:
        messages.error(request, 'Requested quantity exceeds available stock.')
    elif quantity <= 0:
        cart.pop(str(product_id), None)
        messages.success(request, 'Item removed from cart.')
    else:
        cart[str(product_id)] = quantity
        messages.success(request, 'Cart updated successfully!')
    request.session['cart'] = cart
    return redirect('cart')

@login_required
def remove_from_cart(request, product_id):
    if not request.user.profile.is_buyer:
        messages.error(request, 'Access denied. Buyer account required.')
        return redirect('index')
    cart = request.session.get('cart', {})
    cart.pop(str(product_id), None)
    request.session['cart'] = cart
    messages.success(request, 'Item removed from cart.')
    return redirect('cart')

@login_required
def checkout(request, order_id=None):
    if not request.user.profile.is_buyer:
        messages.error(request, 'Access denied.')
        return redirect('index')
    customer = get_object_or_404(Customer, user=request.user)

    # If order_id is provided, use that order (for Buy Now)
    if order_id is not None:
        order = get_object_or_404(Order, id=order_id, customer=customer)
        cart_items = []
        cart_total = 0
        for item in order.items.all():
            cart_items.append({
                'product': item.product,
                'quantity': item.quantity,
                'subtotal': item.price * item.quantity
            })
            cart_total += item.price * item.quantity
    else:
        cart = request.session.get('cart', {})
        if not cart:
            messages.error(request, 'Your cart is empty.')
            return redirect('cart')
        cart_items = []
        cart_total = 0
        for product_id, quantity in cart.items():
            product = get_object_or_404(Product, id=product_id)
            subtotal = product.discounted_price * quantity
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'subtotal': subtotal
            })
            cart_total += subtotal

    address_form = AddressForm()
    supercoin_balance = Supercoin.objects.filter(customer=customer).first().total_balance if Supercoin.objects.filter(customer=customer).exists() else 0
    supercoin_value = Decimal('1')  # 1 Supercoin = ₹1.00
    max_supercoins = min(int(cart_total // supercoin_value), supercoin_balance)
    supercoins_to_use = 0  # Default for GET
    if request.method == "POST":
        supercoins_to_use = int(request.POST.get("supercoins_to_use", 0))
        if "apply_supercoins" in request.POST:
            # Just re-render the page with the new supercoin value and discount
            final_amount = cart_total - (supercoins_to_use * supercoin_value)
            context = {
                'cart_items': cart_items,
                'cart_total': cart_total,
                'categories': Category.objects.filter(is_active=True),
                'customer': customer,
                'address_form': address_form,
                'payment_methods': [
                    ('card', 'Credit/Debit Card'),
                    ('upi', 'UPI'),
                    ('cod', 'Cash on Delivery'),
                ],
                'supercoin_balance': supercoin_balance,
                'max_supercoins': max_supercoins,
                "supercoins_to_use": supercoins_to_use,
                "final_amount": final_amount,
            }
            if order_id is not None:
                context['order'] = order
            return render(request, 'checkout.html', context)
        else:
            # This is the "Complete Order" logic!
            # Validate address, payment, etc.
            # Create the order, deduct supercoins, etc.
            # Then redirect to success page or order detail
            # Example:
            # 1. Validate address and payment_method
            # 2. Create order and order items
            # 3. Deduct supercoins from user
            # 4. Save supercoins_used and supercoin_discount to order
            # 5. Redirect to order confirmation
            address_id = request.POST.get('address_id')
            payment_method = request.POST.get('payment_method')
            if not address_id or not payment_method:
                messages.error(request, "Please select an address and payment method.")
                # Re-render the page with the same context
                final_amount = order.total_price - order.supercoin_discount
                context = {
                    'cart_items': cart_items,
                    'cart_total': cart_total,
                    'categories': Category.objects.filter(is_active=True),
                    'customer': customer,
                    'address_form': address_form,
                    'payment_methods': [
                        ('card', 'Credit/Debit Card'),
                        ('upi', 'UPI'),
                        ('cod', 'Cash on Delivery'),
                    ],
                    'supercoin_balance': supercoin_balance,
                    'max_supercoins': max_supercoins,
                    "supercoins_to_use": supercoins_to_use,
                    "final_amount": final_amount,
                }
                if order_id is not None:
                    context['order'] = order
                return render(request, 'checkout.html', context)

            # Create new address if needed
            if address_id == "new":
                address_form = AddressForm(request.POST)
                if address_form.is_valid():
                    address = address_form.save(commit=False)
                    address.customer = customer
                    address.save()
                else:
                    messages.error(request, "Invalid address provided.")
                    return render(request, 'checkout.html', context)
            else:
                address = Address.objects.get(id=address_id, customer=customer)

            # Create the order
            order = Order.objects.create(
                customer=customer,
                shipping_address=address,
                billing_address=address,
                status='pending',
                supercoins_used=supercoins_to_use,
                supercoin_discount=supercoins_to_use * supercoin_value,
                final_paid=cart_total - (supercoins_to_use * supercoin_value),
                
            )
            # Add order items
            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    quantity=item['quantity'],
                    price=item['product'].discounted_price
                )

            # Deduct supercoins
            if supercoins_to_use > 0:
                Supercoin.objects.create(
                    customer=customer,
                    amount=supercoins_to_use,
                    transaction_type='redeemed',
                    order=order
                )

            # Create Payment object
            payment = Payment.objects.create(
                order=order,
                amount=order.final_paid,
                supercoins_used=supercoins_to_use,
                final_amount=order.final_paid,
                payment_method=payment_method,
                status=Payment.COMPLETED if payment_method != 'cod' else Payment.PENDING
            )

            # Clear cart
            if not order_id:
                request.session['cart'] = {}

            # Redirect based on payment method
            if payment_method in ['card', 'upi']:
                return redirect('spin_wheel', order_id=order.id)
            else:
                return redirect('order_detail', pk=order.id)
    # ...rest of your order placement logic...
    context = {
        'cart_items': cart_items,
        'cart_total': cart_total,
        'categories': Category.objects.filter(is_active=True),
        'customer': customer,
        'address_form': address_form,
        'payment_methods': [
            ('card', 'Credit/Debit Card'),
            ('upi', 'UPI'),
            ('cod', 'Cash on Delivery'),
        ],
        'supercoin_balance': supercoin_balance,
        'max_supercoins': max_supercoins,
        "supercoins_to_use": supercoins_to_use,
    }
    if order_id is not None:
        context['order'] = order
    if 'final_amount' not in context:
        context['final_amount'] = cart_total - (supercoins_to_use * supercoin_value)

    return render(request, 'checkout.html', context)

@login_required
def spin_wheel(request, order_id):
    if not request.user.profile.is_buyer:
        messages.error(request, 'Access denied.')
        return redirect('index')
    order = get_object_or_404(Order, id=order_id, customer__user=request.user)
    payment = getattr(order, 'payment', None)
    if not payment:
        messages.error(request, 'Payment information not found for this order.')
        return redirect('order_detail', pk=order.id)
    if payment.payment_method not in ['card', 'upi']:
        messages.error(request, 'Supercoins are only awarded for UPI or Credit/Debit Card payments.')
        return redirect('order_detail', pk=order.id)
    # Only allow spinning if not already spun
    if request.method == 'POST' and not order.has_spun:
        outcomes = [
            (0, 40),   # 40%
            (10, 25),  # 25%
            (20, 20),  # 20%
            (50, 14),  # 14%
            (10000, 1),  # 1%
        ]
        total_weight = sum(weight for _, weight in outcomes)
        choice = random.uniform(0, total_weight)
        cumulative_weight = 0
        for coins, weight in outcomes:
            cumulative_weight += weight
            if choice <= cumulative_weight:
                supercoin_amount = coins
                break
        order.has_spun = True
        order.spin_prize = supercoin_amount
        order.save()
        if supercoin_amount > 0:
            Supercoin.objects.create(
                customer=order.customer,
                amount=supercoin_amount,
                transaction_type='earned',
                order=order
            )
            messages.success(request, f'Congratulations! You earned {supercoin_amount} Supercoins!')
        else:
            messages.info(request, 'Better luck next time!')
        return redirect('spin_wheel', order_id=order.id)
    return render(request, 'spin_wheel.html', {
        'order': order,
        'categories': Category.objects.filter(is_active=True),
        'redeemed_prize': order.spin_prize if order.has_spun else None,
    })

@login_required
def take_order(request, order_id):
    if not request.user.profile.is_delivery:
        messages.error(request, 'Access denied.')
        return redirect('index')
    delivery_person = get_object_or_404(DeliveryPerson, user=request.user)
    order = get_object_or_404(Order, id=order_id, status='processing', delivery_person__isnull=True)
    order.delivery_person = delivery_person
    order.save()
    messages.success(request, 'You have taken the order.')
    return redirect('delivery_dashboard')

@login_required
def add_review(request, product_id):
    if not request.user.profile.is_buyer:
        messages.error(request, "Only buyers can submit reviews.")
        return redirect('home')
    
    product = get_object_or_404(Product, id=product_id)
    customer = get_object_or_404(Customer, user=request.user)
    order_id = request.POST.get('order_id')
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment', '')
        
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except (TypeError, ValueError):
            messages.error(request, "Invalid rating.")
            return redirect('order_detail', pk=order_id)
        
        order = get_object_or_404(Order, id=order_id, customer=customer, status='delivered')
        
        review, created = Review.objects.update_or_create(
            product=product,
            customer=customer,
            defaults={'rating': rating, 'comment': comment}
        )
        
        messages.success(request, "Review submitted successfully!")
        return redirect('order_detail', pk=order_id)
    
    messages.error(request, "Invalid request.")
    return redirect('order_detail', pk=order_id)

@login_required
def seller_profile(request):
    if not request.user.profile.is_seller:
        messages.error(request, 'Access denied. Seller account required.')
        return redirect('index')
    
    seller_profile = request.user.profile
    seller_stats = {
        'total_products': Product.objects.filter(seller=request.user).count(),
        'total_sales': OrderItem.objects.filter(product__seller=request.user)
                            .aggregate(total=Sum(F('quantity') * F('price')))['total'] or 0,
        'avg_rating': Review.objects.filter(product__seller=request.user)
                       .aggregate(avg=Avg('rating'))['avg']
    }
    
    if request.method == 'POST':
        form = SellerProfileForm(request.POST, request.FILES, instance=seller_profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('seller_profile')
    else:
        form = SellerProfileForm(instance=seller_profile)
    
    return render(request, 'seller_profile.html', {
        'seller_profile': seller_profile,
        'form': form,
        **seller_stats
    })

def home(request):
    categories = Category.objects.filter(is_active=True)
    featured_products = Product.objects.filter(is_active=True, is_featured=True).prefetch_related('reviews')[:8]
    return render(request, 'index.html', {
        'categories': categories,
        'featured_products': featured_products
    })
from django.views.decorators.http import require_POST

@require_POST
@login_required
def buy_now(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    customer = get_object_or_404(Customer, user=request.user)
    # 1. Create the order
    order = Order.objects.create(
        customer=customer,
        status='pending'
    )
    # 2. Add the product as an OrderItem
    OrderItem.objects.create(
        order=order,
        product=product,
        quantity=1,
        price=product.discounted_price  # or product.price if you don't have discounts
    )
    return redirect('checkout', order_id=order.id)

# Duplicate product_detail view removed to avoid "product is not defined" error.

@login_required
def add_address(request):
    if not request.user.profile.is_buyer:
        messages.error(request, 'Access denied. Buyer account required.')
        return redirect('index')
    customer = get_object_or_404(Customer, user=request.user)
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.customer = customer
            address.save()
            messages.success(request, 'Address added successfully!')
            return redirect('customer_profile')
        else:
            messages.error(request, 'Invalid address provided.')
    else:
        form = AddressForm()
    return render(request, 'customer_profile.html', {
        'form': CustomerForm(instance=customer),
        'address_form': form,
        'categories': Category.objects.filter(is_active=True),
        'customer': customer
    })

@login_required
def delete_address(request, pk):
    if not request.user.profile.is_buyer:
        messages.error(request, 'Access denied. Buyer account required.')
        return redirect('index')
    customer = get_object_or_404(Customer, user=request.user)
    address = get_object_or_404(Address, pk=pk, customer=customer)
    if request.method == 'POST':
        if address.is_default:
            messages.error(request, 'Cannot delete default address. Set another address as default first.')
        else:
            address.delete()
            messages.success(request, 'Address deleted successfully!')
        return redirect('customer_profile')
    messages.error(request, 'Invalid request.')
    return redirect('customer_profile')

@login_required
def set_default_address(request, pk):
    if not request.user.profile.is_buyer:
        messages.error(request, 'Access denied. Buyer account required.')
        return redirect('index')
    customer = get_object_or_404(Customer, user=request.user)
    address = get_object_or_404(Address, pk=pk, customer=customer)
    if request.method == 'POST':
        address.is_default = True
        address.save()  # This will automatically unset other default addresses via the Address model's save method
        messages.success(request, 'Default address updated successfully!')
        return redirect('customer_profile')
    messages.error(request, 'Invalid request.')
    return redirect('customer_profile')

@login_required
def buyer_wishlist(request):
    if not request.user.profile.is_buyer:
        messages.error(request, 'Access denied. Buyer account required.')
        return redirect('index')
    customer = get_object_or_404(Customer, user=request.user)
    wishlist, _ = Wishlist.objects.get_or_create(customer=customer)
    return render(request, 'buyer_wishlist.html', {
        'wishlist': wishlist.products.all(),
        'categories': Category.objects.filter(is_active=True)
    })

def about(request):
    return render(request, 'about.html', {'categories': Category.objects.filter(is_active=True)})

@login_required
def contact_us(request):
    categories = Category.objects.filter(is_active=True)
    if request.method == 'POST':
        email = request.user.email
        reason = request.POST.get('reason', '')
        message = request.POST.get('message', '')
        subject = f"Contact Us - {reason}"
        helpline_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'sunilmazhuvangadan@gmail.com')
        body = f"From: {request.user.username} ({email})\n\nReason: {reason}\n\nMessage:\n{message}"
        send_mail(subject, body, email, [helpline_email])
        messages.success(request, "Your message has been sent to our helpline. We'll get back to you soon.")
        return redirect('contact_us')
    return render(request, 'contact_us.html', {'categories': categories})

