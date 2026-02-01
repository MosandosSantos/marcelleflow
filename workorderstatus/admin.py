from django.contrib import admin
from .models import WorkOrderStatus, ServiceOrderStatus


@admin.register(WorkOrderStatus)
class WorkOrderStatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'created_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('name', 'description')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('order', 'name')

    fieldsets = (
        ('Informacoes Principais', {
            'fields': ('name', 'description', 'order')
        }),
        ('Controle', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ServiceOrderStatus)
class ServiceOrderStatusAdmin(admin.ModelAdmin):
    list_display = ('group_name', 'status_name', 'status_code', 'status_order', 'is_final', 'is_active')
    list_filter = ('group_name', 'is_final', 'is_active')
    search_fields = ('group_name', 'status_name', 'status_code')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('status_order', 'group_name', 'status_name')

    fieldsets = (
        ('Grupo', {
            'fields': ('group_code', 'group_name', 'group_color')
        }),
        ('Status', {
            'fields': ('status_code', 'status_name', 'status_order', 'is_final', 'is_active')
        }),
        ('Controle', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
