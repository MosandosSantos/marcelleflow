# workorderstatus/urls.py

from django.urls import path
from . import views

app_name = 'workorderstatus'

urlpatterns = [
    path('', views.WorkOrderStatusListView.as_view(), name='list'),
    path('create/', views.WorkOrderStatusCreateView.as_view(), name='create'),
    path('<uuid:pk>/', views.WorkOrderStatusDetailView.as_view(), name='detail'),
    path('<uuid:pk>/edit/', views.WorkOrderStatusUpdateView.as_view(), name='edit'),
    path('<uuid:pk>/delete/', views.WorkOrderStatusDeleteView.as_view(), name='delete'),
]
