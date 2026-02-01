from django.contrib import admin
from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'cpf', 'cnpj', 'phone', 'city', 'state', 'created_at')
    list_filter = ('state', 'city', 'created_at', 'updated_at')
    search_fields = ('full_name', 'email', 'cpf', 'cnpj', 'phone', 'user__email', 'user__username')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('full_name',)

    fieldsets = (
        ('Informações do Usuário', {
            'fields': ('user',)
        }),
        ('Dados Pessoais', {
            'fields': ('full_name', 'email', 'cpf', 'cnpj', 'phone', 'birth_date')
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
        ('Controle', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    autocomplete_fields = ['user']
