# servicesoperators/urls.py

from django.urls import path
from . import views

app_name = 'servicesoperators'

urlpatterns = [
    path('', views.ServiceOperatorListView.as_view(), name='list'),
    path('create/', views.ServiceOperatorCreateView.as_view(), name='create'),
    path('<uuid:pk>/', views.ServiceOperatorDetailView.as_view(), name='detail'),
    path('<uuid:pk>/edit/', views.ServiceOperatorUpdateView.as_view(), name='edit'),
    path('<uuid:pk>/delete/', views.ServiceOperatorDeleteView.as_view(), name='delete'),
]
