# signals.py
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save  # Import the post_save signal
from django.dispatch import receiver
from django.utils import timezone
from django.contrib.auth.models import User
from .models import Profile


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Auto-create profile for new users"""
    if created:
        Profile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Auto-save profile when user is saved"""
    instance.profile.save()


@receiver(user_logged_in)
def update_last_login(sender, request, user, **kwargs):
    """Update profile's last_login_at when user logs in"""
    if hasattr(user, "profile"):
        user.profile.last_login_at = timezone.now()
        user.profile.save()
