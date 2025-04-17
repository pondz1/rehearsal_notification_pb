from django.contrib import admin

from maintenance.models import MaintenanceCategory


# Register your models here.
@admin.register(MaintenanceCategory)
class MaintenanceCategoryAdmin(admin.ModelAdmin):
    pass