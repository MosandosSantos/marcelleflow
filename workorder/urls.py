from django.urls import path
from . import views

app_name = 'workorder'

urlpatterns = [
    # Listagem e CRUD (admin/manager)
    path('', views.WorkOrderListView.as_view(), name='list'),
    path('calendar/', views.WorkOrderCalendarView.as_view(), name='calendar'),
    path('kanban/', views.WorkOrderKanbanView.as_view(), name='kanban'),
    path('create/', views.WorkOrderCreateView.as_view(), name='create'),
    path('<uuid:pk>/', views.WorkOrderDetailView.as_view(), name='detail'),
    path('<uuid:pk>/edit/', views.WorkOrderUpdateView.as_view(), name='edit'),
    path('<uuid:pk>/delete/', views.delete_work_order, name='delete'),
    path('<uuid:pk>/cancel/', views.cancel_work_order, name='cancel'),
    path('<uuid:pk>/finalize/', views.finalize_work_order, name='finalize'),

    # Visualizações específicas por role
    path('my-orders/', views.my_orders_view, name='my_orders'),  # Prestador
    path('my-requests/', views.my_requests_view, name='my_requests'),  # Cliente

    # Ações de status (prestador)
    path('<uuid:pk>/start/', views.start_work_order, name='start'),
    path('<uuid:pk>/complete/', views.complete_work_order, name='complete'),
    path('cep-lookup/', views.cep_lookup, name='cep_lookup'),

    # Avaliação (cliente)
    path('<uuid:pk>/evaluate/', views.evaluate_work_order, name='evaluate'),
]
