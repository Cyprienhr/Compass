from django.db import models
from django.conf import settings
from employees.models import Employee, Category
from decimal import Decimal


class AttendanceRecord(models.Model):
    PERIOD_CHOICES = [
        ('DAILY', 'Daily'),
        ('WEEKLY', 'Weekly'),
        ('BIWEEKLY', 'Bi-weekly'),
        ('MONTHLY', 'Monthly'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    period_type = models.CharField(max_length=10, choices=PERIOD_CHOICES, default='DAILY')
    periods_worked = models.PositiveIntegerField(default=1)
    deducted = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    date = models.DateField()
    signature = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def compute_total(self) -> None:
        amount = Decimal(str(self.amount)) if self.amount is not None else Decimal('0')
        periods = int(self.periods_worked or 0)
        deducted = Decimal(str(self.deducted or 0))
        bonus = Decimal(str(self.bonus or 0))
        base = amount * periods
        self.total_amount = base - deducted + bonus

    def get_period_display_name(self) -> str:
        """Get human-readable period description"""
        if self.period_type == 'DAILY':
            return f"{self.periods_worked} day(s)"
        elif self.period_type == 'WEEKLY':
            return f"{self.periods_worked} week(s)"
        elif self.period_type == 'BIWEEKLY':
            return f"{self.periods_worked} bi-week(s)"
        elif self.period_type == 'MONTHLY':
            return f"{self.periods_worked} month(s)"
        return f"{self.periods_worked} {self.period_type.lower()}"

    def save(self, *args, **kwargs):
        self.compute_total()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = 'Attendance Record'
        verbose_name_plural = 'Attendance Records'
