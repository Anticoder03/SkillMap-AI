"""Signal handlers for the accounts app."""
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs) -> None:
    """Automatically create a UserProfile whenever a User is created."""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs) -> None:
    getattr(instance, "profile", None) and instance.profile.save()