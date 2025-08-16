from django.db import models
from django.conf import settings
from sites.models import ConstructionSite


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.name


class Employee(models.Model):
    full_name = models.CharField(max_length=255)
    national_id = models.CharField(max_length=50)
    contact = models.CharField(max_length=50, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    site = models.ForeignKey(ConstructionSite, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.full_name} ({self.national_id})"
    
    def get_total_worked_days(self):
        """Get total days worked by this employee (only daily records)"""
        from attendance.models import AttendanceRecord
        return AttendanceRecord.objects.filter(employee=self, period_type='DAILY').count()
    
    def get_total_worked_weeks(self):
        """Get total weeks worked by this employee (only weekly records)"""
        from attendance.models import AttendanceRecord
        return AttendanceRecord.objects.filter(employee=self, period_type='WEEKLY').count()
    
    def get_total_worked_biweeks(self):
        """Get total bi-weeks worked by this employee (only bi-weekly records)"""
        from attendance.models import AttendanceRecord
        return AttendanceRecord.objects.filter(employee=self, period_type='BIWEEKLY').count()
    
    def get_total_worked_months(self):
        """Get total months worked by this employee (only monthly records)"""
        from attendance.models import AttendanceRecord
        return AttendanceRecord.objects.filter(employee=self, period_type='MONTHLY').count()
    
    def get_total_earnings(self):
        """Get total earnings from all attendance records"""
        from attendance.models import AttendanceRecord
        records = AttendanceRecord.objects.filter(employee=self)
        total = 0
        for record in records:
            total += record.total_amount
        return total
    
    def get_earnings_by_period_type(self):
        """Get earnings broken down by period type"""
        from attendance.models import AttendanceRecord
        earnings = {
            'DAILY': 0,
            'WEEKLY': 0,
            'BIWEEKLY': 0,
            'MONTHLY': 0
        }
        records = AttendanceRecord.objects.filter(employee=self)
        for record in records:
            earnings[record.period_type] += record.total_amount
        return earnings
