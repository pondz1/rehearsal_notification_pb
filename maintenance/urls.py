from django.urls import path
from .views import *

app_name = 'maintenance'
urlpatterns = [
    path('', home, name='home'),
    path('list', MaintenanceListView.as_view(), name='maintenance_list'),
    path('create/', MaintenanceCreateView.as_view(), name='maintenance_create'),
    path('job/', MaintenanceJobListView.as_view(), name='maintenance_job'),
    path('detail/<int:pk>/', MaintenanceDetailView.as_view(), name='maintenance_detail'),
    path('<int:pk>/edit/', MaintenanceRequestEditView.as_view(), name='maintenance_edit'),
    path('manage/', MaintenanceManageView.as_view(), name='maintenance_manage'),
    path('manage/executives', MaintenanceExecutivesManageView.as_view(), name='maintenance_executives'),
    path('maintenance/<int:pk>/evaluate/', evaluate_request, name='evaluate_request'),

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

    # API endpoints
    path('api/maintenance/<int:request_id>/assign/', assign_maintenance_request, name='api_assign_request'),
    path('api/maintenance/<int:pk>/status/', update_status, name='update_status'),

    # Evaluation API endpoints
    path('api/maintenance/<int:request_id>/evaluation/', get_maintenance_evaluation,
         name='api_get_evaluation'),
    path('api/maintenance/<int:request_id>/approve-repair/', approve_repair, name='api_approve_repair'),
    path('api/maintenance/<int:request_id>/approve-parts/', approve_parts, name='api_approve_parts'),

    path('pr/', PurchaseRequestListView.as_view(), name='pr_list'),
    path('pr/create/', PurchaseRequestCreateView.as_view(), name='pr_create'),
    path('pr/<int:pk>/', PurchaseRequestDetailView.as_view(), name='pr_detail'),
    path('pr/<int:pk>/approve/', approve_pr, name='pr_approve'),
    path('pr/<int:pk>/reject/', reject_pr, name='pr_reject'),
    path('pr/<int:pk>/edit/', PurchaseRequestUpdateView.as_view(), name='pr_edit'),

    path('api/get-evaluations/<int:maintenance_request_id>/', get_evaluations, name='get_evaluations'),

    path('po/create/<int:pr_id>/', PurchaseOrderCreateView.as_view(), name='po_create'),
    path('po/', PurchaseOrderListView.as_view(), name='po_list'),
    path('po/<int:pk>/', PurchaseOrderDetailView.as_view(), name='po_detail'),
    path('po/<int:pk>/issue/', PurchaseOrderIssueView.as_view(), name='po_issue'),
    path('po/<int:pk>/print/', PurchaseOrderPrintView.as_view(), name='po_print'),
]
