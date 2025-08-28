from django.db import models
from django.conf import settings


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('PAYROLL_SUBMISSION', 'Payroll Submission'),
        ('PAYROLL_REPLY', 'Payroll Reply'),
        ('GENERAL', 'General'),
    ]
    
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_notifications', null=True, blank=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='GENERAL')
    is_read = models.BooleanField(default=False)
    related_date = models.DateField(null=True, blank=True)  # For payroll date
    related_site = models.CharField(max_length=255, blank=True)  # For site info
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.title} -> {self.recipient}"
