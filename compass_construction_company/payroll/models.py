from django.db import models
from employees.models import Employee, Category
from decimal import Decimal


class PayrollRecord(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    deducted = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    contact = models.CharField(max_length=50, blank=True)
    signature = models.BooleanField(default=False)
    payment_status = models.CharField(
        max_length=20,
        choices=[('PAID', 'Paid'), ('PENDING', 'Pending'), ('PARTIAL', 'Partial')],
        default='PENDING',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def compute_total(self) -> None:
        amount = Decimal(str(self.amount)) if self.amount is not None else Decimal('0')
        deducted = Decimal(str(self.deducted or 0))
        bonus = Decimal(str(self.bonus or 0))
        total = amount - deducted + bonus
        self.total_paid = total if total > 0 else Decimal('0')

    def save(self, *args, **kwargs):
        self.compute_total()
        super().save(*args, **kwargs)
