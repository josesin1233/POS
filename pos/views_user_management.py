"""
Vistas para el sistema de gestión de usuarios y registro único
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
import json
import logging

from .models_user_management import UserRegistration, UserRegistrationLog
from accounts.models import User, Business

logger = logging.getLogger(__name__)


def subscription_form_view(request):
    """
    Vista que renderiza el formulario de suscripción
    (ya existe en suscripcion_nueva.html)
    """
    return render(request, 'pos/suscripcion_nueva.html')


@csrf_exempt
@require_http_methods(["POST"])
def process_subscription_form(request):
    """
    Procesa el formulario de contacto inicial y crea UserRegistration
    """
    try:
        # Obtener datos del formulario
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        full_name = data.get('full_name', '').strip()
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        city = data.get('city', '').strip()

        # Validaciones básicas
        if not all([full_name, email, phone, city]):
            return JsonResponse({
                'success': False,
                'error': 'Todos los campos son obligatorios'
            }, status=400)

        # Validar email
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({
                'success': False,
                'error': 'El formato del email no es válido'
            }, status=400)

        # Verificar si el email ya existe
        if UserRegistration.objects.filter(email=email).exists():
            return JsonResponse({
                'success': False,
                'error': 'Este email ya está registrado en nuestro sistema'
            }, status=400)

        # Crear el registro
        registration = UserRegistration.objects.create(
            full_name=full_name,
            email=email,
            phone=phone,
            city=city,
            status='nuevo',
            source='formulario_web'
        )

        # Log de la acción
        UserRegistrationLog.objects.create(
            registration=registration,
            action='form_submitted',
            description=f'Formulario web enviado desde IP: {get_client_ip(request)}'
        )

        logger.info(f"Nueva suscripción creada: {registration.full_name} ({registration.email})")

        return JsonResponse({
            'success': True,
            'message': '¡Información enviada exitosamente! Te contactaremos pronto.',
            'registration_id': registration.pk
        })

    except Exception as e:
        logger.error(f"Error procesando formulario de suscripción: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Error interno del servidor. Por favor intenta de nuevo.'
        }, status=500)


def complete_registration(request, token):
    """
    Vista para completar el registro usando el token único
    """
    registration = get_object_or_404(UserRegistration, registration_token=token)

    # Verificar si el token es válido
    if not registration.is_token_valid():
        if registration.token_used:
            messages.error(request, 'Este link de registro ya fue utilizado.')
            return redirect('user_management:registration_invalid')
        else:
            messages.error(request, 'Este link de registro ha expirado.')
            return redirect('user_management:registration_expired')

    if request.method == 'POST':
        try:
            # Obtener datos del formulario de negocio
            business_name = request.POST.get('business_name', '').strip()
            business_address = request.POST.get('business_address', '').strip()
            business_type = request.POST.get('business_type', 'dulceria')
            password = request.POST.get('password', '').strip()
            password_confirm = request.POST.get('password_confirm', '').strip()

            # Validaciones
            if not all([business_name, business_address, password]):
                messages.error(request, 'Todos los campos marcados con * son obligatorios')
                raise ValidationError('Campos requeridos faltantes')

            if password != password_confirm:
                messages.error(request, 'Las contraseñas no coinciden')
                raise ValidationError('Contraseñas no coinciden')

            if len(password) < 8:
                messages.error(request, 'La contraseña debe tener al menos 8 caracteres')
                raise ValidationError('Contraseña muy corta')

            # Crear usuario
            user = User.objects.create_user(
                email=registration.email,
                first_name=registration.full_name.split()[0],
                last_name=' '.join(registration.full_name.split()[1:]),
                phone=registration.phone,
                password=password
            )

            # Crear negocio
            business = Business.objects.create(
                name=business_name,
                address=business_address,
                business_type=business_type,
                city=registration.city,
                owner=user
            )

            # Actualizar registro
            registration.pos_user = user
            registration.business = business
            registration.use_token()  # Marca token como usado y avanza estado

            # Log de la acción
            UserRegistrationLog.objects.create(
                registration=registration,
                action='registration_completed',
                description=f'Usuario y negocio creados exitosamente. Business: {business_name}',
                created_by=user
            )

            logger.info(f"Registro completado: {user.email} - Negocio: {business_name}")

            messages.success(request, '¡Registro completado exitosamente! Ya puedes iniciar sesión.')
            return redirect('user_management:registration_success')

        except Exception as e:
            logger.error(f"Error completando registro: {str(e)}")
            messages.error(request, 'Error al completar el registro. Por favor intenta de nuevo.')

    # GET: mostrar formulario
    context = {
        'registration': registration,
        'token_expires_in': (registration.token_expires_at - timezone.now()).total_seconds() / 3600 if registration.token_expires_at else 72
    }
    return render(request, 'pos/complete_registration.html', context)


def registration_success(request):
    """Vista de éxito tras completar registro"""
    return render(request, 'pos/registration_success.html')


def registration_expired(request):
    """Vista para token expirado"""
    return render(request, 'pos/registration_expired.html')


def registration_invalid(request):
    """Vista para token inválido"""
    return render(request, 'pos/registration_invalid.html')


@csrf_exempt
@require_http_methods(["POST"])
def update_user_status(request, registration_id):
    """
    API endpoint para actualizar estado de usuario (usado desde admin)
    """
    try:
        if not request.user.is_staff:
            return JsonResponse({'error': 'No autorizado'}, status=403)

        registration = get_object_or_404(UserRegistration, pk=registration_id)
        data = json.loads(request.body)
        new_status = data.get('status')

        if new_status and registration.advance_status(new_status):
            # Log de la acción
            UserRegistrationLog.objects.create(
                registration=registration,
                action=f'status_updated',
                description=f'Estado actualizado a: {new_status}',
                created_by=request.user
            )

            return JsonResponse({
                'success': True,
                'new_status': registration.get_status_display(),
                'progress': registration.get_timeline_progress()
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'No se puede actualizar a este estado'
            }, status=400)

    except Exception as e:
        logger.error(f"Error actualizando estado: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Error interno del servidor'
        }, status=500)


def get_client_ip(request):
    """Helper para obtener IP del cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip