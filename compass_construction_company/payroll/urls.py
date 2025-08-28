from django.urls import path
from . import views

urlpatterns = [
    path('', views.payroll_list, name='payroll_list'),
    path('upsert-for-date/', views.payroll_upsert_for_date, name='payroll_upsert_for_date'),
    path('bulk-upsert-for-date/', views.payroll_bulk_upsert_for_date, name='payroll_bulk_upsert_for_date'),
    path('submit-to-chief/', views.payroll_submit_to_chief, name='payroll_submit_to_chief'),
    path('reply-from-chief/', views.payroll_reply_from_chief, name='payroll_reply_from_chief'),
]
