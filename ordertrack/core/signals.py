from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, DeliveryPerson

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance, defaults={'role': 'buyer'})
    else:
        if hasattr(instance, 'profile'):
            instance.profile.save()
            # Create DeliveryPerson if role is delivery
            if instance.profile.role == 'delivery' and not hasattr(instance, 'delivery_person'):
                DeliveryPerson.objects.get_or_create(
                    user=instance,
                    defaults={
                        'name': instance.username,
                        'phone': '',
                    }
                )