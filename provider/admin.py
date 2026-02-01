from django.contrib import admin
from .models import Provider


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'cpf', 'phone', 'city', 'state', 'created_at')
    list_filter = ('state', 'city', 'service_types', 'created_at', 'updated_at')
    search_fields = ('full_name', 'email', 'cpf', 'phone', 'user__email', 'user__username')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('full_name',)
    filter_horizontal = ('service_types',)

    fieldsets = (
        ('Informações do Usuário', {
            'fields': ('user',)
        }),
        ('Dados Pessoais', {
            'fields': ('full_name', 'email', 'cpf', 'phone', 'birth_date')
        }),
        ('Endereço', {
            'fields': (
                ('street', 'number'),
                'complement',
                'neighborhood',
                ('city', 'state'),
                'zip_code'
            )
        }),
        ('Dados Bancários', {
            'fields': ('bank_name', 'bank_agency', 'bank_account', 'bank_pix_key')
        }),
        ('Serviços', {
            'fields': ('service_types',)
        }),
        ('Observações', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Controle', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    autocomplete_fields = ['user']
