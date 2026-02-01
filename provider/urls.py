# provider/urls.py

from django.urls import path
from . import views

app_name = 'provider'

urlpatterns = [
    path('', views.ProviderListView.as_view(), name='list'),
    path('create/', views.ProviderCreateView.as_view(), name='create'),
    path('<uuid:pk>/', views.ProviderDetailView.as_view(), name='detail'),
    path('<uuid:pk>/edit/', views.ProviderUpdateView.as_view(), name='edit'),
    path('<uuid:pk>/delete/', views.ProviderDeleteView.as_view(), name='delete'),
    path('<uuid:pk>/history/', views.ProviderHistoryView.as_view(), name='history'),
]
