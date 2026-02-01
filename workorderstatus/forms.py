# workorderstatus/forms.py

from django import forms
from .models import ServiceOrderStatus


class WorkOrderStatusForm(forms.ModelForm):
    class Meta:
        model = ServiceOrderStatus
        fields = [
            'group_code', 'group_name', 'group_color',
            'status_code', 'status_name', 'status_order',
            'is_final', 'is_active'
        ]
        widgets = {
            'group_code': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50'}),
            'group_name': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50'}),
            'group_color': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50'}),
            'status_code': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50'}),
            'status_name': forms.TextInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50'}),
            'status_order': forms.NumberInput(attrs={'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50'}),
            'is_final': forms.CheckboxInput(attrs={'class': 'rounded border-gray-300 text-primary shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'rounded border-gray-300 text-primary shadow-sm focus:border-primary focus:ring focus:ring-primary focus:ring-opacity-50'}),
        }
