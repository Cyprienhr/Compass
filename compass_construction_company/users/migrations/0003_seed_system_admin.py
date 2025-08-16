from django.db import migrations


def seed_admin(apps, schema_editor):
    User = apps.get_model('users', 'User')
    if not User.objects.filter(username='Cyprienhr').exists():
        user = User.objects.create_superuser(
            username='Cyprienhr',
            password='Rwendere@2001',
            email='cyprienhagena01@gmail.com',
            first_name='Rwendere',
            last_name='Cyprien',
        )
        user.role = 'SYSTEM_ADMIN'
        user.phone = '+250787140195'
        user.national_id = '1200180036027040'
        user.save(update_fields=['role', 'phone', 'national_id'])


def unseed_admin(apps, schema_editor):
    User = apps.get_model('users', 'User')
    User.objects.filter(username='Cyprienhr').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0002_create_default_admin'),
    ]

    operations = [
        migrations.RunPython(seed_admin, unseed_admin),
    ]


