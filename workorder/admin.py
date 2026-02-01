from django.contrib import admin
from .models import WorkOrder


class WorkOrderHistoryInline(admin.TabularInline):
    model = None  # Will be set dynamically to avoid circular import
    extra = 0
    can_delete = False
    readonly_fields = ('previous_status', 'new_status', 'changed_by', 'note', 'created_at')
    fields = ('previous_status', 'new_status', 'changed_by', 'note', 'created_at')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'client',
        'provider',
        'service_type',
        'status',
        'scheduled_date',
        'is_active',
        'created_at'
    )
    list_filter = (
        'status',
        'service_type',
        'is_active',
        'scheduled_date',
        'created_at',
        'updated_at',
        'insurance_company',
        'service_operator'
    )
    search_fields = (
        'code',
        'client__full_name',
        'client__cpf',
        'provider__full_name',
        'description',
        'technical_report'
    )
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    date_hierarchy = 'scheduled_date'

    fieldsets = (
        ('Identificação', {
            'fields': ('code', 'status', 'is_active')
        }),
        ('Relacionamentos', {
            'fields': (
                'client',
                'provider',
                'service_type',
                'insurance_company',
                'service_operator'
            )
        }),
        ('Descrição do Serviço', {
            'fields': ('description', 'technical_report')
        }),
        ('Datas', {
            'fields': (
                'scheduled_date',
                'started_at',
                'finished_at'
            )
        }),
        ('Métricas de Tempo', {
            'fields': ('estimated_time_minutes', 'real_time_minutes'),
            'classes': ('collapse',)
        }),
        ('Financeiro', {
            'fields': ('labor_cost',),
            'classes': ('collapse',)
        }),
        ('Controle', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    autocomplete_fields = ['client', 'provider']

    def get_inlines(self, request, obj):
        # Dynamically import to avoid circular import
        if obj:
            from workorderhistory.models import WorkOrderHistory
            WorkOrderHistoryInline.model = WorkOrderHistory
            return [WorkOrderHistoryInline]
        return []
