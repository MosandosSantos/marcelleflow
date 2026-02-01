"""
Mixins de permissão centralizados para controle de acesso baseado em roles.

Este módulo contém mixins que substituem os IsAdminOrManagerMixin dispersos
pelos apps, centralizando a lógica de permissões para os 5 roles do sistema.
"""
from django.contrib.auth.mixins import UserPassesTestMixin


class IsAdminMixin(UserPassesTestMixin):
    """
    Apenas Administrador tem acesso.
    Usado para operações críticas que requerem nível máximo de permissão.
    """
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.role == 'admin'


class IsAdminOrOperationalMixin(UserPassesTestMixin):
    """
    Admin ou Operacional - Para OS e Cadastros.

    Controla acesso a:
    - Ordens de Serviço (CRUD completo)
    - Cadastros de Clientes, Prestadores, Tipos de Serviço (CRUD completo)
    """
    def test_func(self):
        user = self.request.user
        return user.is_superuser or user.role in ['admin', 'operational']


class IsWorkOrderReadOnlyMixin(UserPassesTestMixin):
    """
    Admin, Operacional ou Financeiro - Leitura de OS.

    Usado em listagens e visualizacao de OS.
    """
    def test_func(self):
        user = self.request.user
        return user.is_superuser or user.role in ['admin', 'operational', 'financial']


class IsFinancialMixin(UserPassesTestMixin):
    """
    Admin ou Financeiro - Para módulo financeiro.

    Controla acesso a:
    - Transações (CRUD - visualização consolidada de todos usuários)
    - DRE e Fluxo de Caixa (visualização consolidada)
    - Contas e Categorias (CRUD)
    """
    def test_func(self):
        user = self.request.user
        return (
            user.is_superuser
            or user.role in ['admin', 'financial']
            or (user.is_staff and user.role != 'operational')
        )


class IsFinancialReadOnlyClientsMixin(UserPassesTestMixin):
    """
    Controle especial para acesso de Financeiro aos Clientes.

    - Admin e Operational: Acesso completo (GET/POST/PUT/DELETE)
    - Financial: Somente leitura (GET)
    - Outros: Sem acesso

    Usado nas views de Clientes para permitir que o financeiro consulte
    informações de clientes sem poder editar/criar/excluir.
    """
    def test_func(self):
        user = self.request.user

        # Admin e Operational têm acesso total
        if user.is_superuser or user.role in ['admin', 'operational']:
            return True

        # Financial só pode fazer GET (leitura)
        if user.role == 'financial':
            return self.request.method == 'GET'

        return False
