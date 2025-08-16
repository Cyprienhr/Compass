from django.urls import path
from . import views

urlpatterns = [
    path('', views.attendance_list, name='attendance_list'),
    path('summary/', views.attendance_summary, name='attendance_summary'),
    path('create/', views.attendance_create, name='attendance_create'),
    path('<int:record_id>/edit/', views.attendance_edit, name='attendance_edit'),
    path('<int:record_id>/delete/', views.attendance_delete, name='attendance_delete'),
]
