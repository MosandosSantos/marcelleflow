"""
Backend de autenticação customizado para login SEM senha.
ATENÇÃO: Isso é apenas para desenvolvimento! NÃO use em produção!
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class NoPasswordBackend(ModelBackend):
    """
    Backend que permite login apenas com email (SEM verificação de senha).

    Este backend é para fins de DESENVOLVIMENTO/DEMONSTRAÇÃO APENAS.
    Em produção, sempre use autenticação com senha segura.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Autentica o usuário apenas pelo email, ignorando a senha.

        Args:
            username: Email do usuário (pois USERNAME_FIELD='email')
            password: Ignorado neste backend

        Returns:
            User object se encontrado, None caso contrário
        """
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)

        try:
            # Busca usuário pelo email
            user = User.objects.get(**{User.USERNAME_FIELD: username})

            # Não verifica senha - apenas retorna o usuário
            return user

        except User.DoesNotExist:
            # Usuário não existe
            return None

    def get_user(self, user_id):
        """
        Retorna o usuário pelo ID.
        Método obrigatório do backend.
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
