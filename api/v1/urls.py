from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet,
    ClientViewSet,
    InsuranceCompanyViewSet,
    ServiceTypeViewSet,
    CostItemViewSet,
    ServiceCostViewSet,
    TaxProfileViewSet,
    ProviderViewSet,
    WorkOrderStatusViewSet,
    ServiceOperatorViewSet,
    WorkOrderViewSet,
    WorkOrderHistoryViewSet
)

router = DefaultRouter()

# Register all viewsets
router.register(r'users', UserViewSet, basename='user')
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'insurance-companies', InsuranceCompanyViewSet, basename='insurancecompany')
router.register(r'service-types', ServiceTypeViewSet, basename='servicetype')
router.register(r'cost-items', CostItemViewSet, basename='costitem')
router.register(r'service-costs', ServiceCostViewSet, basename='servicecost')
router.register(r'tax-profiles', TaxProfileViewSet, basename='taxprofile')
router.register(r'providers', ProviderViewSet, basename='provider')
router.register(r'work-order-statuses', WorkOrderStatusViewSet, basename='workorderstatus')
router.register(r'service-operators', ServiceOperatorViewSet, basename='serviceoperator')
router.register(r'work-orders', WorkOrderViewSet, basename='workorder')
router.register(r'work-order-history', WorkOrderHistoryViewSet, basename='workorderhistory')

urlpatterns = [
    path('', include(router.urls)),
]
