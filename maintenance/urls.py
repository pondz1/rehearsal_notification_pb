from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'maintenance-requests', MaintenanceRequestViewSet)
router.register(r'maintenance-categories', MaintenanceCategoryViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
    path('', MaintenanceListView.as_view(), name='maintenance_list'),
    path('create/', MaintenanceCreateView.as_view(), name='maintenance_create'),
    path('detail/<int:pk>/', MaintenanceDetailView.as_view(), name='maintenance_detail'),

]
