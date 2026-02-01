from decimal import Decimal

from rest_framework import serializers
from django.contrib.auth import get_user_model
from clients.models import Client
from insurancecompany.models import InsuranceCompany
from provider.models import Provider
from servicetype.models import CostItem, ServiceCost, ServiceType, TaxProfile
from workorderstatus.models import ServiceOrderStatus
from servicesoperators.models import ServiceOperator
from workorder.models import WorkOrder
from workorderhistory.models import WorkOrderHistory

from servicetype.services import simulate_service_pricing

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'is_active', 'is_staff', 'date_joined', 'last_login'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'password', 'password_confirm'
        ]
        read_only_fields = ['id']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ClientSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Client
        fields = [
            'id', 'user', 'user_email', 'user_username',
            'full_name', 'email', 'cpf', 'cnpj', 'phone', 'birth_date',
            'street', 'number', 'complement', 'neighborhood',
            'city', 'state', 'zip_code',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class InsuranceCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = InsuranceCompany
        fields = [
            'id', 'name', 'trade_name', 'document',
            'contact_email', 'contact_phone', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        from clients.validators import is_valid_cpf, is_valid_cnpj, normalize_digits

        cpf = attrs.get('cpf')
        cnpj = attrs.get('cnpj')
        if self.instance:
            cpf = cpf if cpf is not None else self.instance.cpf
            cnpj = cnpj if cnpj is not None else self.instance.cnpj
        if not cpf and not cnpj:
            raise serializers.ValidationError('Informe CPF ou CNPJ.')
        if cpf and cnpj:
            raise serializers.ValidationError('Informe apenas CPF ou apenas CNPJ.')

        if cpf:
            cpf_norm = normalize_digits(cpf)
            if not is_valid_cpf(cpf_norm):
                raise serializers.ValidationError({'cpf': 'CPF inválido.'})
            attrs['cpf'] = cpf_norm

        if cnpj:
            cnpj_norm = normalize_digits(cnpj)
            if not is_valid_cnpj(cnpj_norm):
                raise serializers.ValidationError({'cnpj': 'CNPJ inválido.'})
            attrs['cnpj'] = cnpj_norm
        return attrs


class TaxProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxProfile
        fields = [
            'id', 'name', 'iss', 'federal_taxes', 'financial_fees',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CostItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CostItem
        fields = [
            'id', 'name', 'description', 'cost_type',
            'billing_unit', 'unit_cost', 'is_active',
            'expense_group', 'cost_behavior',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ServiceCostSerializer(serializers.ModelSerializer):
    service_type_name = serializers.CharField(source='service_type.name', read_only=True)
    cost_item_name = serializers.CharField(source='cost_item.name', read_only=True)

    class Meta:
        model = ServiceCost
        fields = [
            'id', 'service_type', 'service_type_name',
            'cost_item', 'cost_item_name',
            'quantity', 'unit_cost_snapshot',
            'is_required', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ServiceTypeSerializer(serializers.ModelSerializer):
    tax_profile = serializers.PrimaryKeyRelatedField(
        queryset=TaxProfile.objects.all(),
        allow_null=True,
        required=False
    )
    tax_profile_details = TaxProfileSerializer(source='tax_profile', read_only=True)
    service_costs = ServiceCostSerializer(many=True, read_only=True)
    pricing_preview = serializers.SerializerMethodField()

    class Meta:
        model = ServiceType
        fields = [
            'id', 'name', 'description', 'ferramentas',
            'duracao_estimada', 'duracao_media', 'billing_unit',
            'unit_price', 'estimated_price', 'default_quantity',
            'tax_profile', 'tax_profile_details',
            'margin_target', 'margin_minimum', 'volume_baseline',
            'is_active', 'created_at', 'updated_at',
            'service_costs', 'pricing_preview'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'service_costs', 'pricing_preview']

    def get_pricing_preview(self, obj):
        return simulate_service_pricing(obj)


class ServicePricingSimulationSerializer(serializers.Serializer):
    margin = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, min_value=Decimal('0.00'), max_value=Decimal('100.00'))
    cost_adjustment = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    tax_rate_delta = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    volume = serializers.IntegerField(required=False, min_value=1)


class ServicePricingResultSerializer(serializers.Serializer):
    direct_cost = serializers.DecimalField(max_digits=12, decimal_places=2)
    tax_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    tax_total = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_before_margin = serializers.DecimalField(max_digits=12, decimal_places=2)
    margin_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    margin_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    volume = serializers.IntegerField()
    revenue = serializers.DecimalField(max_digits=15, decimal_places=2)
    profit = serializers.DecimalField(max_digits=15, decimal_places=2)
    profit_margin_pct = serializers.DecimalField(max_digits=5, decimal_places=2)


class ProviderSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    service_types_details = ServiceTypeSerializer(source='service_types', many=True, read_only=True)

    class Meta:
        model = Provider
        fields = [
            'id', 'user', 'user_email', 'user_username',
            'full_name', 'email', 'cpf', 'phone', 'birth_date',
            'street', 'number', 'complement', 'neighborhood',
            'city', 'state', 'zip_code',
            'bank_name', 'bank_agency', 'bank_account', 'bank_pix_key',
            'notes', 'service_types', 'service_types_details',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WorkOrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceOrderStatus
        fields = [
            'id', 'group_code', 'group_name', 'group_color', 'status_code', 'status_name', 'status_order', 'is_final', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ServiceOperatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceOperator
        fields = [
            'id', 'name', 'trade_name', 'cnpj',
            'responsible_name', 'responsible_role',
            'email', 'phone', 'website',
            'street', 'number', 'complement', 'district',
            'city', 'state', 'zip_code',
            'is_active', 'notes'
        ]
        read_only_fields = ['id']


class WorkOrderHistorySerializer(serializers.ModelSerializer):
    work_order_code = serializers.CharField(source='work_order.code', read_only=True)
    previous_status_name = serializers.CharField(source='previous_status.status_name', read_only=True)
    new_status_name = serializers.CharField(source='new_status.status_name', read_only=True)
    changed_by_email = serializers.EmailField(source='changed_by.email', read_only=True)

    class Meta:
        model = WorkOrderHistory
        fields = [
            'id', 'work_order', 'work_order_code',
            'previous_status', 'previous_status_name',
            'new_status', 'new_status_name',
            'changed_by', 'changed_by_email',
            'note', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class WorkOrderSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    provider_name = serializers.CharField(source='provider.full_name', read_only=True)
    service_type_name = serializers.CharField(source='service_type.name', read_only=True)
    status_name = serializers.CharField(source='status.status_name', read_only=True)
    insurance_company_name = serializers.CharField(source='insurance_company.name', read_only=True)
    service_operator_name = serializers.CharField(source='service_operator.name', read_only=True)
    history = WorkOrderHistorySerializer(many=True, read_only=True)

    class Meta:
        model = WorkOrder
        fields = [
            'id', 'code',
            'client', 'client_name',
            'provider', 'provider_name',
            'service_type', 'service_type_name',
            'address',
            'insurance_company', 'insurance_company_name',
            'service_operator', 'service_operator_name',
            'technical_report',
            'actions',
            'status', 'status_name',
            'description',
            'scheduled_date', 'started_at', 'finished_at',
            'estimated_time_minutes', 'real_time_minutes',
            'labor_cost', 'is_active',
            'created_at', 'updated_at',
            'history'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        client = attrs.get('client')
        if self.instance:
            client = client if client is not None else self.instance.client
        if not client:
            raise serializers.ValidationError({'client': 'Selecione um cliente cadastrado.'})
        return attrs


class WorkOrderListSerializer(serializers.ModelSerializer):
    """Simplified serializer for list views"""
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    provider_name = serializers.CharField(source='provider.full_name', read_only=True)
    service_type_name = serializers.CharField(source='service_type.name', read_only=True)
    status_name = serializers.CharField(source='status.status_name', read_only=True)
    insurance_company_name = serializers.CharField(source='insurance_company.name', read_only=True)
    service_operator_name = serializers.CharField(source='service_operator.name', read_only=True)

    class Meta:
        model = WorkOrder
        fields = [
            'id', 'code',
            'client_name', 'provider_name',
            'service_type_name', 'address',
            'insurance_company_name', 'service_operator_name',
            'status_name',
            'scheduled_date', 'is_active', 'created_at'
        ]
