from django.urls import path
from . import views

urlpatterns = [
    path('', views.employee_list, name='employee_list'),
    path('create/', views.employee_create, name='employee_create'),
    path('<int:employee_id>/edit/', views.employee_edit, name='employee_edit'),
    path('<int:employee_id>/toggle/', views.employee_toggle_active, name='employee_toggle_active'),
    path('<int:employee_id>/delete/', views.employee_delete, name='employee_delete'),
    path('<int:employee_id>/json/', views.employee_json, name='employee_json'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
]
