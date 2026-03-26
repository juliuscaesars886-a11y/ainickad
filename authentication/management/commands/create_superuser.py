from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

User = get_user_model()

class Command(BaseCommand):
    help = "Create superuser for UserProfile model"

    def handle(self, *args, **options):
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "superadmin@ainick.com")
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "Superadmin@098")
        
        self.stdout.write(f"Creating superuser: {email}")
        
        try:
            # Delete if exists
            if User.objects.filter(email=email).exists():
                User.objects.filter(email=email).delete()
                self.stdout.write(self.style.WARNING(f"Deleted existing user: {email}"))
            
            # Create superuser
            user = User.objects.create_superuser(
                email=email,
                password=password
            )
            self.stdout.write(self.style.SUCCESS(f"Superuser created: {email}"))
            self.stdout.write(f"  Role: {user.role}")
            self.stdout.write(f"  Is Staff: {user.is_staff}")
            self.stdout.write(f"  Is Superuser: {user.is_superuser}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
            import traceback
            traceback.print_exc()
