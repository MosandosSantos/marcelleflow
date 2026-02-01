from django.urls import path
from .views import custom_login_view, CustomLogoutView, ClientRegisterView, UserProfileView

app_name = 'accounts'

urlpatterns = [
    path('login/', custom_login_view, name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('register/', ClientRegisterView.as_view(), name='register'),
    path('profile/', UserProfileView.as_view(), name='profile'),
]
