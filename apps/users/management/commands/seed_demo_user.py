"""
Management command to seed a demo admin user for the Tag Along demo.

Usage:
    python manage.py seed_demo_user
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create a demo admin user for the Tag Along demo (admin@tagalong.app / TagAlong2024Demo)'

    def handle(self, *args, **options):
        User = get_user_model()

        email = 'admin@tagalong.app'
        password = 'TagAlong2024Demo'

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': 'admin',
                'first_name': 'Admin',
                'last_name': 'User',
                'is_staff': True,
                'is_superuser': True,
                'is_active': True,
            },
        )

        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created demo admin user: {email} / {password}'
                )
            )
        else:
            # Ensure password is correct even if user already existed
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.is_active = True
            user.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Demo admin user already exists, password reset to: {email} / {password}'
                )
            )
