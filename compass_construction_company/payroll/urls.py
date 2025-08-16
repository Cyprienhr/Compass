from django.urls import path
from . import views

urlpatterns = [
    path('', views.payroll_list, name='payroll_list'),
    path('create/', views.payroll_create, name='payroll_create'),
    path('<int:record_id>/edit/', views.payroll_edit, name='payroll_edit'),
    path('<int:record_id>/delete/', views.payroll_delete, name='payroll_delete'),
    path('<int:record_id>/status/', views.payroll_update_status, name='payroll_update_status'),
    path('<int:record_id>/sign/', views.payroll_sign, name='payroll_sign'),
]
