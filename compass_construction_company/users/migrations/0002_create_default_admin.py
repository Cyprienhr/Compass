from django.db import migrations
from django.conf import settings


def create_default_admin(apps, schema_editor):
    User = apps.get_model('users', 'User')
    if not User.objects.filter(username='admin').exists():
        user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123',
        )
        user.role = 'SYSTEM_ADMIN'
        user.save(update_fields=['role'])


def remove_default_admin(apps, schema_editor):
    User = apps.get_model('users', 'User')
    User.objects.filter(username='admin').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_admin, remove_default_admin),
    ]


