# servicetype/urls.py

from django.urls import path
from . import views

app_name = 'servicetype'

urlpatterns = [
    path('', views.ServiceTypeListView.as_view(), name='list'),
    path('dashboards/', views.ServiceTypeDashboardView.as_view(), name='dashboards'),
    path('create/', views.ServiceTypeCreateView.as_view(), name='create'),
    path('<uuid:pk>/', views.ServiceTypeDetailView.as_view(), name='detail'),
    path('<uuid:pk>/edit/', views.ServiceTypeUpdateView.as_view(), name='edit'),
    path('<uuid:pk>/delete/', views.ServiceTypeDeleteView.as_view(), name='delete'),
    path('<uuid:pk>/providers/', views.ServiceTypeProvidersView.as_view(), name='providers'),

    # Cost Items (Itens de Custo)
    # Cost items e composição de custos - em breve
    path('cost-items/', views.ServiceTypeComingSoonView.as_view(), name='costitem_list'),
    path('cost-items/create/', views.ServiceTypeComingSoonView.as_view(), name='costitem_create'),
    path('cost-items/<uuid:pk>/', views.ServiceTypeComingSoonView.as_view(), name='costitem_detail'),
    path('cost-items/<uuid:pk>/edit/', views.ServiceTypeComingSoonView.as_view(), name='costitem_edit'),
    path('cost-items/<uuid:pk>/delete/', views.ServiceTypeComingSoonView.as_view(), name='costitem_delete'),

    # Service Costs (Composição de Custos)
    # service costs - em breve
    path('service-costs/', views.ServiceTypeComingSoonView.as_view(), name='servicecost_list'),
    path('service-costs/create/', views.ServiceTypeComingSoonView.as_view(), name='servicecost_create'),
    path('service-costs/<uuid:pk>/', views.ServiceTypeComingSoonView.as_view(), name='servicecost_detail'),
    path('service-costs/<uuid:pk>/edit/', views.ServiceTypeComingSoonView.as_view(), name='servicecost_edit'),
    path('service-costs/<uuid:pk>/delete/', views.ServiceTypeComingSoonView.as_view(), name='servicecost_delete'),

    # Profit Margin Analysis (Análise de Margem de Lucro)
    # análise de margem - em breve
    path('profit-analysis/', views.ServiceTypeComingSoonView.as_view(), name='profit_analysis'),
    path('<uuid:pk>/profit-detail/', views.ServiceTypeProfitDetailView.as_view(), name='profit_detail'),
]
