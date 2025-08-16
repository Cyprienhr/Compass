from django.urls import path
from . import views

urlpatterns = [
    path('', views.site_list, name='site_list'),
    path('create/', views.site_create, name='site_create'),
    path('<int:site_id>/assign/', views.site_assign, name='site_assign'),
    path('<int:site_id>/edit/', views.site_edit, name='site_edit'),
    path('<int:site_id>/delete/', views.site_delete, name='site_delete'),
]
