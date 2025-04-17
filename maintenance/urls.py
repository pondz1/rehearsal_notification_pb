from django.urls import path
from .views import *

app_name = 'maintenance'
urlpatterns = [
    path('', MaintenanceListView.as_view(), name='maintenance_list'),
    path('create/', MaintenanceCreateView.as_view(), name='maintenance_create'),
    path('detail/<int:pk>/', MaintenanceDetailView.as_view(), name='maintenance_detail'),
    path('manage/', MaintenanceManageView.as_view(), name='maintenance_manage'),
    path('api/maintenance/<int:pk>/status/', update_status, name='update_status'),
    path('api/maintenance/<int:pk>/approve/', approve_request, name='approve_request'),

    # New URLs
    # Profile & Settings
    path('profile/', ProfileView.as_view(), name='profile'),
    path('settings/', SettingsView.as_view(), name='settings'),

    # Reports
    path('reports/', ReportsView.as_view(), name='reports'),
    path('reports/export/', export_reports, name='export_reports'),

    # Notifications
    path('notifications/', NotificationListView.as_view(), name='notifications'),
    path('notifications/mark-read/', mark_notifications_read, name='mark_notifications_read'),
    path('notifications/api/count/', get_unread_count, name='notification_count'),

    # API Endpoints
    path('api/maintenance/filter/', filter_maintenance, name='filter_maintenance'),
    path('api/technicians/', get_technicians, name='get_technicians'),
    # path('api/departments/', get_departments, name='get_departments'),
]
