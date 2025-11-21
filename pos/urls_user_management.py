"""
URLs para el sistema de gestión de usuarios y registro único
"""
from django.urls import path
from . import views_user_management

app_name = 'user_management'

urlpatterns = [
    # Formulario de suscripción inicial (ya existe)
    path('suscripcion/', views_user_management.subscription_form_view, name='subscription_form'),

    # Procesamiento del formulario
    path('suscripcion/submit/', views_user_management.process_subscription_form, name='process_form'),

    # Sistema de links únicos
    path('registro/complete/<uuid:token>/', views_user_management.complete_registration, name='complete_registration'),

    # Páginas de resultado
    path('registro/success/', views_user_management.registration_success, name='registration_success'),
    path('registro/expired/', views_user_management.registration_expired, name='registration_expired'),
    path('registro/invalid/', views_user_management.registration_invalid, name='registration_invalid'),

    # API endpoints para admin
    path('api/user-registration/<int:registration_id>/status/', views_user_management.update_user_status, name='update_status'),
]