from django.urls import path
from . import views

urlpatterns = [
    path('', views.notification_list, name='notification_list'),
    path('<int:notif_id>/read/', views.notification_mark_read, name='notification_mark_read'),
]
