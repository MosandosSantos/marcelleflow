from django.contrib import admin
from .models import ServiceOperator


@admin.register(ServiceOperator)
class ServiceOperatorAdmin(admin.ModelAdmin):
    list_display = ('name', 'trade_name', 'cnpj', 'email', 'phone', 'city', 'state', 'is_active')
    list_filter = ('is_active', 'state', 'city')
    search_fields = ('name', 'trade_name', 'cnpj', 'email', 'phone', 'responsible_name')
    readonly_fields = ('id',)
    ordering = ('name',)

    fieldsets = (
        ('Informações da Empresa', {
            'fields': ('name', 'trade_name', 'cnpj')
        }),
        ('Responsável', {
            'fields': ('responsible_name', 'responsible_role')
        }),
        ('Contato', {
            'fields': ('email', 'phone', 'website')
        }),
        ('Endereço', {
            'fields': (
                ('street', 'number'),
                'complement',
                'district',
                ('city', 'state'),
                'zip_code'
            )
        }),
        ('Status e Observações', {
            'fields': ('is_active', 'notes')
        }),
        ('Controle', {
            'fields': ('id',),
            'classes': ('collapse',)
        }),
    )
