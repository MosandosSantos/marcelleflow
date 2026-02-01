"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from .views import landing_page
from .dashboard_views import dashboard_router, mapa_sla_api, service_x

schema_view = get_schema_view(
    openapi.Info(
        title="EsferaWork API",
        default_version='v1',
        description="""
        API REST para o Sistema de Gestão de Ordens de Serviço - EsferaWork

        ## Recursos Disponíveis
        - Gerenciamento de Usuários e Autenticação
        - Cadastro de Clientes
        - Cadastro de Prestadores de Serviço
        - Tipos de Serviço
        - Catálogo de Custos e itens reutilizáveis
        - Associação entre Serviços e Custos (precificação)
        - Seguradoras
        - Operadoras de Serviço
        - Ordens de Serviço (Work Orders)
        - Histórico de Mudanças de Status

        ## Autenticação
        A API usa autenticação de sessão do Django e autenticação básica HTTP.
        """,
        terms_of_service="https://www.esferawork.com/terms/",
        contact=openapi.Contact(email="contact@esferawork.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # API REST (já existente)
    path('api/', include('api.urls')),

    # Swagger/OpenAPI documentation
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # Frontend URLs
    path('', landing_page, name='landing'),
    path('', include('accounts.urls')),  # /login/, /logout/, /register/
    path('dashboard/', dashboard_router, name='dashboard'),
    path('servico-x/', service_x, name='service-x'),
    path('api/dashboard/mapa-sla/', mapa_sla_api, name='mapa-sla-api'),
    path('orders/', include('workorder.urls')),  # /orders/...
    path('clients/', include('clients.urls')),  # /clients/...
    path('providers/', include('provider.urls')),  # /providers/...
    path('service-types/', include('servicetype.urls')),  # /service-types/...
    path('insurance-companies/', include('insurancecompany.urls')),  # /insurance-companies/...
    path('service-operators/', include('servicesoperators.urls')),  # /service-operators/...
    path('financeiro/', include('finance.urls')),
]
