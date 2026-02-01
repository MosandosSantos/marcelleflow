# insurancecompany/urls.py

from django.urls import path
from . import views

app_name = 'insurancecompany'

urlpatterns = [
    path('', views.InsuranceCompanyListView.as_view(), name='list'),
    path('create/', views.InsuranceCompanyCreateView.as_view(), name='create'),
    path('<uuid:pk>/', views.InsuranceCompanyDetailView.as_view(), name='detail'),
    path('<uuid:pk>/edit/', views.InsuranceCompanyUpdateView.as_view(), name='edit'),
    path('<uuid:pk>/delete/', views.InsuranceCompanyDeleteView.as_view(), name='delete'),
]
