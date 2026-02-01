from django.contrib import admin
from .models import WorkOrderHistory


@admin.register(WorkOrderHistory)
class WorkOrderHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'work_order',
        'previous_status',
        'new_status',
        'changed_by',
        'created_at'
    )
    list_filter = (
        'previous_status',
        'new_status',
        'created_at',
        'changed_by'
    )
    search_fields = (
        'work_order__code',
        'note',
        'changed_by__email',
        'changed_by__username'
    )
    readonly_fields = ('id', 'created_at')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Ordem de Serviço', {
            'fields': ('work_order',)
        }),
        ('Mudança de Status', {
            'fields': ('previous_status', 'new_status')
        }),
        ('Usuário e Observação', {
            'fields': ('changed_by', 'note')
        }),
        ('Controle', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        # História é criada automaticamente, não manualmente
        return False

    def has_change_permission(self, request, obj=None):
        # História não deve ser editada
        return False

    def has_delete_permission(self, request, obj=None):
        # História não deve ser deletada
        return False
