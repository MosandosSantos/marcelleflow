from django.contrib import admin

from .models import Account, Category, Transaction


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('nome', 'bank_code', 'agencia', 'conta_numero', 'tipo', 'saldo_inicial', 'ativa', 'user')
    list_filter = ('tipo', 'ativa')
    search_fields = ('nome', 'user__email')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo', 'dre_group', 'ativa')
    list_filter = ('tipo', 'dre_group', 'ativa')
    search_fields = ('nome',)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'tipo', 'expense_type', 'status', 'valor', 'data_vencimento', 'is_recurring', 'user')
    list_filter = ('tipo', 'status', 'expense_type', 'is_recurring', 'recurrence_period')
    search_fields = ('descricao', 'user__email')
    date_hierarchy = 'data_vencimento'
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('user', 'tipo', 'descricao', 'valor', 'account', 'category')
        }),
        ('Datas', {
            'fields': ('data_vencimento', 'data_pagamento', 'status')
        }),
        ('Tipificação de Despesas', {
            'fields': ('expense_type', 'related_service_type'),
            'classes': ('collapse',),
        }),
        ('Recorrência', {
            'fields': ('is_recurring', 'recurrence_period'),
            'classes': ('collapse',),
        }),
        ('Observações', {
            'fields': ('observacoes',),
            'classes': ('collapse',),
        }),
    )
