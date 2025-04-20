# admin.py
from django.contrib import admin
from django.db import models
from django.utils.html import format_html

from .models import MaintenanceCategory, Vendor, Part


@admin.register(MaintenanceCategory)
class MaintenanceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    list_per_page = 20

    fieldsets = (
        (None, {
            'fields': ('name', 'description')
        }),
        ('สถานะ', {
            'fields': ('is_active',)
        }),
    )


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ['name', 'contact_person', 'phone', 'email', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'contact_person', 'phone', 'email', 'tax_id']
    list_per_page = 20

    fieldsets = (
        ('ข้อมูลทั่วไป', {
            'fields': ('name', 'tax_id', 'is_active')
        }),
        ('ข้อมูลติดต่อ', {
            'fields': ('contact_person', 'phone', 'email', 'address')
        }),
        ('ข้อมูลเพิ่มเติม', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ['name', 'part_number', 'stock_status', 'stock_quantity', 'minimum_stock', 'cost', 'category']
    list_filter = ['category', 'unit']
    search_fields = ['name', 'part_number', 'description']
    list_per_page = 20

    def stock_status(self, obj):
        if obj.stock_quantity <= 0:
            return format_html('<span style="color: red; font-weight: bold;">หมดสต๊อก</span>')
        elif obj.needs_reorder:
            return format_html('<span style="color: orange; font-weight: bold;">ต้องสั่งเพิ่ม</span>')
        else:
            return format_html('<span style="color: green;">ปกติ</span>')

    stock_status.short_description = "สถานะสินค้า"

    fieldsets = (
        ('ข้อมูลพื้นฐาน', {
            'fields': ('name', 'part_number', 'description', 'category')
        }),
        ('ข้อมูลสต๊อก', {
            'fields': ('stock_quantity', 'minimum_stock', 'unit'),
        }),
        ('ข้อมูลราคา', {
            'fields': ('cost',),
        }),
    )

    actions = ['mark_for_reorder']

    def mark_for_reorder(self, request, queryset):
        # เพิ่มหมายเหตุหรือแท็กให้กับอะไหล่ที่ต้องสั่งเพิ่ม (สามารถปรับแต่งตามความต้องการ)
        updated = queryset.update(minimum_stock=models.F('stock_quantity') + 5)
        self.message_user(request, f'ปรับปรุงจำนวนขั้นต่ำสำหรับ {updated} รายการ')

    mark_for_reorder.short_description = "ปรับปรุงจำนวนขั้นต่ำที่ต้องมี"
