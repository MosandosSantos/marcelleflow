from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from drf_yasg.utils import swagger_auto_schema

from clients.models import Client
from insurancecompany.models import InsuranceCompany
from provider.models import Provider
from servicetype.models import CostItem, ServiceCost, ServiceType, TaxProfile
from servicetype.services import simulate_service_pricing
from workorderstatus.models import ServiceOrderStatus
from servicesoperators.models import ServiceOperator
from workorder.models import WorkOrder
from workorderhistory.models import WorkOrderHistory

from .serializers import (
    UserSerializer, UserCreateSerializer,
    ClientSerializer,
    InsuranceCompanySerializer,
    ProviderSerializer,
    ServiceTypeSerializer,
    CostItemSerializer,
    ServiceCostSerializer,
    TaxProfileSerializer,
    ServicePricingSimulationSerializer,
    ServicePricingResultSerializer,
    WorkOrderStatusSerializer,
    ServiceOperatorSerializer,
    WorkOrderSerializer, WorkOrderListSerializer,
    WorkOrderHistorySerializer
)

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'is_active', 'is_staff']
    search_fields = ['email', 'username', 'first_name', 'last_name']
    ordering_fields = ['email', 'date_joined']
    ordering = ['email']

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user profile"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.select_related('user').all()
    serializer_class = ClientSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['state', 'city']
    search_fields = ['full_name', 'email', 'cpf', 'cnpj', 'phone', 'user__email']
    ordering_fields = ['full_name', 'created_at']
    ordering = ['full_name']


class InsuranceCompanyViewSet(viewsets.ModelViewSet):
    queryset = InsuranceCompany.objects.all()
    serializer_class = InsuranceCompanySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'trade_name', 'document']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class ServiceTypeViewSet(viewsets.ModelViewSet):
    """CRUD de tipos de serviço com informações de precificação e custos associados."""
    queryset = ServiceType.objects.all()
    serializer_class = ServiceTypeSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'billing_unit', 'tax_profile']
    search_fields = ['name', 'description', 'ferramentas']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    @swagger_auto_schema(
        method='post',
        request_body=ServicePricingSimulationSerializer,
        responses={200: ServicePricingResultSerializer()}
    )
    @action(detail=True, methods=['post'])
    def simulate(self, request, pk=None):
        """Simula preço, margem e faturamento com alterações de custos, impostos e volume."""
        serializer = ServicePricingSimulationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service_type = self.get_object()
        result = simulate_service_pricing(
            service_type,
            margin_rate=serializer.validated_data.get('margin'),
            cost_adjustment=serializer.validated_data.get('cost_adjustment'),
            tax_rate_delta=serializer.validated_data.get('tax_rate_delta'),
            volume=serializer.validated_data.get('volume'),
        )
        return Response(result)


class CostItemViewSet(viewsets.ModelViewSet):
    """Gerencia o catálogo de itens de custo reutilizáveis."""
    queryset = CostItem.objects.all()
    serializer_class = CostItemSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['cost_type', 'billing_unit', 'expense_group', 'cost_behavior', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class ServiceCostViewSet(viewsets.ModelViewSet):
    """Associa serviços e custos para compor a precificação completa."""
    queryset = ServiceCost.objects.select_related('service_type', 'cost_item')
    serializer_class = ServiceCostSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['service_type', 'cost_item', 'is_required']
    search_fields = ['service_type__name', 'cost_item__name']
    ordering_fields = ['service_type', 'cost_item', 'created_at']
    ordering = ['-created_at']


class TaxProfileViewSet(viewsets.ModelViewSet):
    """Gerencia perfis fiscais usados no cálculo de impostos."""
    queryset = TaxProfile.objects.all()
    serializer_class = TaxProfileSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class ProviderViewSet(viewsets.ModelViewSet):
    queryset = Provider.objects.select_related('user').prefetch_related('service_types').all()
    serializer_class = ProviderSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['state', 'city', 'service_types']
    search_fields = ['full_name', 'email', 'cpf', 'phone', 'user__email']
    ordering_fields = ['full_name', 'created_at']
    ordering = ['full_name']


class WorkOrderStatusViewSet(viewsets.ModelViewSet):
    queryset = ServiceOrderStatus.objects.all()
    serializer_class = WorkOrderStatusSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['group_name', 'status_name', 'status_code']
    ordering_fields = ['status_order', 'group_name', 'status_name', 'created_at']
    ordering = ['status_order', 'group_name', 'status_name']


class ServiceOperatorViewSet(viewsets.ModelViewSet):
    queryset = ServiceOperator.objects.all()
    serializer_class = ServiceOperatorSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'state', 'city']
    search_fields = ['name', 'trade_name', 'cnpj', 'email', 'responsible_name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class WorkOrderViewSet(viewsets.ModelViewSet):
    queryset = WorkOrder.objects.select_related(
        'client', 'provider', 'service_type', 'status',
        'insurance_company', 'service_operator'
    ).prefetch_related('history').all()
    serializer_class = WorkOrderSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'status', 'service_type', 'is_active',
        'client', 'provider', 'insurance_company', 'service_operator'
    ]
    search_fields = [
        'code', 'client__full_name', 'client__cpf',
        'provider__full_name', 'description'
    ]
    ordering_fields = ['code', 'scheduled_date', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return WorkOrderListSerializer
        return WorkOrderSerializer

    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        """Change work order status and create history entry"""
        work_order = self.get_object()
        new_status_id = request.data.get('status_id')
        note = request.data.get('note', '')

        if not new_status_id:
            return Response(
                {'error': 'status_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            new_status = ServiceOrderStatus.objects.get(id=new_status_id)
        except ServiceOrderStatus.DoesNotExist:
            return Response(
                {'error': 'Status not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Create history entry
        WorkOrderHistory.objects.create(
            work_order=work_order,
            previous_status=work_order.status,
            new_status=new_status,
            changed_by=request.user if request.user.is_authenticated else None,
            note=note
        )

        # Update work order status
        work_order.status = new_status
        work_order.save()

        serializer = self.get_serializer(work_order)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_status(self, request):
        """Get work orders grouped by status"""
        status_id = request.query_params.get('status')
        if status_id:
            queryset = self.get_queryset().filter(status_id=status_id)
        else:
            queryset = self.get_queryset()

        serializer = WorkOrderListSerializer(queryset, many=True)
        return Response(serializer.data)


class WorkOrderHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WorkOrderHistory.objects.select_related(
        'work_order', 'previous_status', 'new_status', 'changed_by'
    ).all()
    serializer_class = WorkOrderHistorySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['work_order', 'previous_status', 'new_status', 'changed_by']
    search_fields = ['work_order__code', 'note']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
