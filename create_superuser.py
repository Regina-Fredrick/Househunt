import os
import django
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

username = os.environ.get('SUPERUSER_USERNAME', 'admin')
email = os.environ.get('SUPERUSER_EMAIL', 'fredrickregina3@gmail.com')
password = os.environ.get('SUPERUSER_PASSWORD', 'HouseHunt2026!')

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Superuser '{username}' created successfully")
else:
    print(f"Superuser '{username}' already exists")