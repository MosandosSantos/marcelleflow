from django.contrib import admin
from .models import InsuranceCompany


@admin.register(InsuranceCompany)
class InsuranceCompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'trade_name', 'document', 'contact_name', 'contact_email', 'contact_phone', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at', 'updated_at')
    search_fields = ('name', 'trade_name', 'document', 'contact_name', 'contact_email', 'contact_phone')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('name',)

    fieldsets = (
        ('Informações Principais', {
            'fields': ('name', 'trade_name', 'document')
        }),
        ('Contato', {
            'fields': ('contact_name', 'contact_email', 'contact_phone')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Controle', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
