"""
Views gerais do projeto.
"""
from django.shortcuts import render, redirect


def landing_page(request):
    """
    Landing page pública do sistema.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'base/landing.html')
