from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    class Roles(models.TextChoices):
        SYSTEM_ADMIN = 'SYSTEM_ADMIN', 'System Admin'
        CHIEF_ENGINEER = 'CHIEF_ENGINEER', 'Chief Engineer'
        SITE_ENGINEER = 'SITE_ENGINEER', 'Site Engineer'

    role = models.CharField(
        max_length=32,
        choices=Roles.choices,
        default=Roles.SITE_ENGINEER,
    )
    phone = models.CharField(max_length=32, blank=True)
    national_id = models.CharField(max_length=32, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def is_system_admin(self) -> bool:
        return self.role == self.Roles.SYSTEM_ADMIN or self.is_superuser

    def is_chief_engineer(self) -> bool:
        return self.role == self.Roles.CHIEF_ENGINEER

    def is_site_engineer(self) -> bool:
        return self.role == self.Roles.SITE_ENGINEER
