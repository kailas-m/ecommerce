from .models import Supercoin, Customer

def supercoin_context(request):
    if request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.role == 'buyer':
        try:
            customer = Customer.objects.get(user=request.user)
            supercoin_obj = Supercoin.objects.filter(customer=customer).first()
            return {'supercoin_balance': supercoin_obj.total_balance if supercoin_obj else 0}
        except Customer.DoesNotExist:
            return {'supercoin_balance': 0}
    return {'supercoin_balance': 0}
