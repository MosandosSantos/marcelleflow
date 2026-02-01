from django.contrib import admin

from .models import CostItem, ServiceCost, ServiceType, TaxProfile


class ServiceCostInline(admin.TabularInline):
    model = ServiceCost
    extra = 0
    autocomplete_fields = ('cost_item',)
    fields = (
        'cost_item',
        'quantity',
        'unit_cost_snapshot',
        'is_required',
        'notes',
    )
    verbose_name = 'Custo do serviço'
    verbose_name_plural = 'Custos do serviço'


@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'margin_target', 'margin_minimum', 'volume_baseline', 'is_active', 'created_at')
    list_filter = ('is_active', 'tax_profile')
    search_fields = ('name', 'description', 'ferramentas')
    readonly_fields = ('id', 'created_at', 'updated_at')
    ordering = ('name',)
    fieldsets = (
        ('Informações Principais', {
            'fields': ('name', 'description')
        }),
        ('Detalhes do Serviço', {
            'fields': ('ferramentas', 'duracao_estimada', 'duracao_media', 'billing_unit')
        }),
        ('Precificação', {
            'fields': ('tax_profile', 'margin_target', 'margin_minimum', 'volume_baseline', 'is_active')
        }),
        ('Controle', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    inlines = (ServiceCostInline,)


@admin.register(CostItem)
class CostItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'expense_group', 'cost_behavior', 'unit_cost', 'is_active')
    list_filter = ('expense_group', 'cost_behavior', 'cost_type', 'billing_unit', 'is_active')
    search_fields = ('name', 'description')
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        ('Identificação', {'fields': ('name', 'description')}),
        ('Detalhes do custo', {'fields': ('cost_type', 'billing_unit', 'unit_cost')}),
        ('Status', {'fields': ('is_active',)}),
        ('Controle', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ServiceCost)
class ServiceCostAdmin(admin.ModelAdmin):
    list_display = ('service_type', 'cost_item', 'quantity', 'is_required', 'created_at')
    list_filter = ('is_required', 'service_type', 'cost_item')
    search_fields = ('service_type__name', 'cost_item__name')
    autocomplete_fields = ('service_type', 'cost_item')
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('service_type', 'cost_item', 'quantity')}),
        ('Valor', {'fields': ('unit_cost_snapshot',)}),
        ('Status', {'fields': ('is_required',)}),
        ('Notas', {'fields': ('notes',)}),
        ('Controle', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TaxProfile)
class TaxProfileAdmin(admin.ModelAdmin):
    list_display = ('name', 'iss', 'federal_taxes', 'financial_fees', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        ('Identificação', {'fields': ('name',)}),
        ('Alíquotas', {'fields': ('iss', 'federal_taxes', 'financial_fees')}),
        ('Status', {'fields': ('is_active',)}),
        ('Controle', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
