from django.urls import path
from . import views

app_name = 'scan'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/start/', views.start_scan, name='start_scan'),
    path('api/history/', views.get_scan_history, name='scan_history'),
    path('api/details/<int:scan_id>/', views.get_scan_details, name='scan_details'),
]
