from django.urls import path
from . import views

urlpatterns = [
    path('', views.payroll_list, name='payroll_list'),
    path('upsert-for-date/', views.payroll_upsert_for_date, name='payroll_upsert_for_date'),
    path('bulk-upsert-for-date/', views.payroll_bulk_upsert_for_date, name='payroll_bulk_upsert_for_date'),
]
