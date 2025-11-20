"""
Views para el sistema de suscripciones
Preparado para conectar con gateway de pagos
"""

import json
import uuid
from decimal import Decimal
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from datetime import datetime, timedelta
from django.db import transaction
import logging
from django.conf import settings

from accounts.models import Business, User
from .models import (
    SubscriptionPlan,
    SubscriptionRegistration,
    PaymentTransaction,
    Suscripcion
)


def subscription_page(request):
    """Nueva página unificada de suscripción"""
    from django.conf import settings
    context = {
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY
    }
    return render(request, 'pos/suscripcion_nueva.html', context)


@csrf_exempt
@require_http_methods(["POST"])
def register_subscription(request):
    """
    API para registrar nueva suscripción
    Preparada para integración con gateway de pagos
    """
    try:
        data = json.loads(request.body)

        # Validar plan seleccionado
        plan = get_object_or_404(SubscriptionPlan, name=data['selected_plan'])

        # Validar datos requeridos
        required_fields = [
            'admin_username', 'admin_password', 'admin_first_name', 'admin_last_name',
            'contact_email', 'contact_phone', 'business_name', 'business_type',
            'address', 'state', 'country'
        ]

        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'error': f'El campo {field} es requerido'
                }, status=400)

        # Verificar que el username no exista
        if User.objects.filter(username=data['admin_username']).exists():
            return JsonResponse({
                'error': 'El nombre de usuario ya está en uso'
            }, status=400)

        # Verificar que el email no exista
        if User.objects.filter(email=data['contact_email']).exists():
            return JsonResponse({
                'error': 'El email ya está registrado'
            }, status=400)

        with transaction.atomic():
            # Crear registro de suscripción temporal
            subscription_registration = SubscriptionRegistration.objects.create(
                business_name=data['business_name'],
                business_type=data['business_type'],
                address=data['address'],
                state=data['state'],
                country=data['country'],
                contact_email=data['contact_email'],
                contact_phone=data['contact_phone'],
                admin_username=data['admin_username'],
                admin_password=make_password(data['admin_password']),
                admin_first_name=data['admin_first_name'],
                admin_last_name=data['admin_last_name'],
                selected_plan=plan
            )

            # TODO: Aquí se integrará el gateway de pagos
            # Por ahora, procesamos manualmente
            result = process_manual_registration(subscription_registration)

            return JsonResponse({
                'success': True,
                'registration_id': subscription_registration.id,
                'message': 'Registro exitoso. Te contactaremos pronto.',
                **result
            })

    except Exception as e:
        return JsonResponse({
            'error': f'Error interno: {str(e)}'
        }, status=500)


def process_manual_registration(registration):
    """
    Procesa el registro manualmente (sin pago)
    En el futuro, esto será llamado después del pago exitoso
    """
    try:
        with transaction.atomic():
            # Crear el negocio
            business = Business.objects.create(
                name=registration.business_name,
                email=registration.contact_email,
                phone=registration.contact_phone,
                address=registration.address,
                max_concurrent_users=registration.selected_plan.max_concurrent_users,
                subscription_active=True,  # Se activará después del pago
                plan_actual=registration.selected_plan.name,
                monthly_cost=registration.selected_plan.price
            )

            # Crear el usuario administrador
            admin_user = User.objects.create(
                username=registration.admin_username,
                password=registration.admin_password,
                first_name=registration.admin_first_name,
                last_name=registration.admin_last_name,
                email=registration.contact_email,
                phone=registration.contact_phone,
                is_business_owner=True,
                business=business,
                is_active=True  # Se activará después del pago
            )

            # Crear suscripción inicial
            start_date = timezone.now()
            end_date = start_date + timedelta(days=registration.selected_plan.duration_days)

            subscription = Suscripcion.objects.create(
                business=business,
                plan=registration.selected_plan.name,
                monto=registration.selected_plan.price,
                fecha_inicio=start_date,
                fecha_fin=end_date,
                estado='pendiente',  # Cambiará a 'activa' después del pago
                metodo_pago='pendiente'
            )

            # Crear transacción de pago pendiente
            transaction_id = f"REG_{registration.id}_{uuid.uuid4().hex[:8]}"

            payment_transaction = PaymentTransaction.objects.create(
                transaction_id=transaction_id,
                business=business,
                subscription=subscription,
                plan=registration.selected_plan,
                amount=registration.selected_plan.price,
                currency='MXN',
                gateway='manual',  # Cambiar según el gateway
                status='pending'
            )

            # Vincular transacción con registro
            registration.payment_transaction = payment_transaction
            registration.save()

            return {
                'business_id': business.id,
                'user_id': admin_user.id,
                'subscription_id': subscription.id,
                'transaction_id': transaction_id
            }

    except Exception as e:
        raise Exception(f"Error procesando registro: {str(e)}")


@csrf_exempt
@require_http_methods(["POST"])
def process_payment(request):
    """
    API preparada para procesar pagos con gateway externo

    PLUG & PLAY: Aquí conectarás tu gateway preferido
    """
    try:
        data = json.loads(request.body)

        registration_id = data.get('registration_id')
        payment_method = data.get('payment_method')  # 'stripe', 'paypal', etc.

        registration = get_object_or_404(
            SubscriptionRegistration,
            id=registration_id,
            is_completed=False
        )

        # Procesar pago con Stripe
        if payment_method == 'stripe' or not payment_method:
            stripe_result = process_stripe_payment(data, registration)

            # Guardar información de Stripe en la transacción
            payment_transaction = registration.payment_transaction
            payment_transaction.gateway_transaction_id = stripe_result['payment_intent_id']
            payment_transaction.gateway_response = {
                'customer_id': stripe_result['customer_id'],
                'payment_intent_id': stripe_result['payment_intent_id'],
                'price_id': stripe_result.get('price_id', '')
            }
            payment_transaction.save()

            return JsonResponse({
                'success': True,
                'client_secret': stripe_result['client_secret'],
                'message': 'Continúa con el pago',
                'payment_method': 'stripe'
            })

        # Por ahora, simular otros gateways
        gateway_response = {
            'status': 'completed',
            'gateway_transaction_id': f"MOCK_{uuid.uuid4().hex[:12]}",
            'timestamp': timezone.now().isoformat()
        }

        # Activar suscripción
        result = activate_subscription(registration, gateway_response)

        return JsonResponse({
            'success': True,
            'message': 'Pago procesado exitosamente',
            **result
        })

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger = logging.getLogger(__name__)
        logger.error(f"Error procesando pago: {str(e)}")
        logger.error(f"Traceback: {error_details}")
        return JsonResponse({
            'error': f'Error procesando pago: {str(e)}',
            'details': error_details if settings.DEBUG else None
        }, status=500)


def activate_subscription(registration, gateway_response):
    """
    Activa la suscripción después de un pago exitoso
    """
    try:
        with transaction.atomic():
            # Actualizar transacción de pago
            payment_transaction = registration.payment_transaction
            payment_transaction.status = 'completed'
            payment_transaction.gateway_response = gateway_response
            payment_transaction.gateway_transaction_id = gateway_response.get('gateway_transaction_id')
            payment_transaction.processed_at = timezone.now()
            payment_transaction.save()

            # Activar business
            business = Business.objects.get(name=registration.business_name)
            business.subscription_active = True
            business.save()

            # Activar usuario
            user = User.objects.get(username=registration.admin_username)
            user.is_active = True
            user.save()

            # Activar suscripción
            subscription = payment_transaction.subscription
            subscription.estado = 'activa'
            subscription.metodo_pago = payment_transaction.gateway
            subscription.transaction_id = payment_transaction.gateway_transaction_id
            subscription.save()

            # Marcar registro como completado
            registration.is_completed = True
            registration.completed_at = timezone.now()
            registration.save()

            return {
                'business_id': business.id,
                'user_id': user.id,
                'subscription_id': subscription.id,
                'login_url': f'/accounts/login/?next=/punto_de_venta/'
            }

    except Exception as e:
        raise Exception(f"Error activando suscripción: {str(e)}")


@csrf_exempt
@require_http_methods(["POST"])
def payment_webhook(request):
    """
    Webhook para recibir notificaciones del gateway de pagos

    PLUG & PLAY: Configurar según tu gateway
    """
    try:
        # TODO: Validar firma del webhook según el gateway
        # stripe_signature = request.headers.get('Stripe-Signature')
        # paypal_signature = request.headers.get('PayPal-Auth-Algo')

        data = json.loads(request.body)

        # TODO: Procesar según el tipo de evento
        # if data.get('type') == 'payment_intent.succeeded':  # Stripe
        # if data.get('event_type') == 'PAYMENT.CAPTURE.COMPLETED':  # PayPal

        transaction_id = data.get('transaction_id')
        status = data.get('status')

        if transaction_id and status == 'completed':
            # Buscar transacción y activar
            payment = PaymentTransaction.objects.get(
                gateway_transaction_id=transaction_id
            )

            registration = SubscriptionRegistration.objects.get(
                payment_transaction=payment
            )

            result = activate_subscription(registration, data)

        return JsonResponse({'received': True})

    except Exception as e:
        return JsonResponse({
            'error': f'Error procesando webhook: {str(e)}'
        }, status=500)


def get_subscription_plans(request):
    """API para obtener planes disponibles"""
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('hierarchy_level')

    plans_data = []
    for plan in plans:
        features = []
        for feature in plan.features.all():
            features.append({
                'name': feature.name,
                'description': feature.description,
                'feature_key': feature.feature_key
            })

        plans_data.append({
            'id': plan.id,
            'name': plan.name,
            'display_name': plan.display_name,
            'description': plan.description,
            'price': float(plan.price),
            'max_concurrent_users': plan.max_concurrent_users,
            'duration_days': plan.duration_days,
            'hierarchy_level': plan.hierarchy_level,
            'is_promotional': plan.is_promotional,
            'promotional_text': plan.promotional_text,
            'features': features
        })

    return JsonResponse({
        'plans': plans_data
    })


# ====================================
# FUNCIONES PARA CONECTAR GATEWAYS
# ====================================

def process_stripe_payment(data, registration):
    """
    Función activa para procesar pagos con Stripe
    """
    import stripe
    from django.conf import settings

    stripe.api_key = settings.STRIPE_SECRET_KEY
    stripe.api_version = settings.STRIPE_API_VERSION

    try:
        # Mapear plan names a Price IDs
        plan_price_mapping = {
            'estandar': 'price_1SVJWPPYEj8hTUzFQ7xNYwQR',
            'pro': 'price_1SVJWQPYEj8hTUzFuUemzeeP'
        }

        price_id = plan_price_mapping.get(registration.selected_plan.name)
        if not price_id:
            raise Exception(f"Plan no encontrado: {registration.selected_plan.name}")

        # Crear Customer en Stripe
        customer = stripe.Customer.create(
            email=registration.contact_email,
            name=f"{registration.admin_first_name} {registration.admin_last_name}",
            metadata={
                'registration_id': registration.id,
                'business_name': registration.business_name
            }
        )

        # Crear PaymentIntent primero
        payment_intent = stripe.PaymentIntent.create(
            amount=int(registration.selected_plan.price * 100),  # en centavos
            currency='mxn',
            customer=customer.id,
            metadata={
                'registration_id': registration.id,
                'business_name': registration.business_name,
                'plan_name': registration.selected_plan.name
            },
            automatic_payment_methods={'enabled': True}
        )

        return {
            'client_secret': payment_intent.client_secret,
            'payment_intent_id': payment_intent.id,
            'customer_id': customer.id,
            'price_id': price_id
        }

    except stripe.error.StripeError as e:
        raise Exception(f"Error de Stripe: {str(e)}")
    except Exception as e:
        raise Exception(f"Error procesando pago: {str(e)}")


def process_paypal_payment(data, registration):
    """
    Función preparada para PayPal

    INSTRUCCIONES PARA CONECTAR:
    1. pip install paypalrestsdk
    2. Configurar PAYPAL_CLIENT_ID y PAYPAL_CLIENT_SECRET
    3. Descomentar y configurar esta función
    """
    # import paypalrestsdk

    # paypalrestsdk.configure({
    #     "mode": "sandbox",  # o "live" para producción
    #     "client_id": settings.PAYPAL_CLIENT_ID,
    #     "client_secret": settings.PAYPAL_CLIENT_SECRET
    # })

    # payment = paypalrestsdk.Payment({
    #     "intent": "sale",
    #     "payer": {"payment_method": "paypal"},
    #     "redirect_urls": {
    #         "return_url": f"{settings.BASE_URL}/subscription/paypal/success/",
    #         "cancel_url": f"{settings.BASE_URL}/subscription/paypal/cancel/"
    #     },
    #     "transactions": [{
    #         "amount": {
    #             "total": str(registration.selected_plan.price),
    #             "currency": "MXN"
    #         },
    #         "description": f"Suscripción {registration.selected_plan.display_name}"
    #     }]
    # })

    # if payment.create():
    #     return {"payment_id": payment.id}
    # else:
    #     raise Exception(f"Error de PayPal: {payment.error}")

    pass


@csrf_exempt
@require_http_methods(["POST"])
def complete_business_registration(request):
    """Complete business registration after successful payment"""
    try:
        data = json.loads(request.body)
        registration_id = data.get('registration_id')

        # Get the registration record
        registration = SubscriptionRegistration.objects.get(id=registration_id)

        # Update business information
        registration.business_name = data.get('business_name')
        registration.business_type = data.get('business_type')
        registration.rfc = data.get('rfc', '')
        registration.address = data.get('address')
        registration.city = data.get('city')
        registration.state = data.get('state')
        registration.postal_code = data.get('postal_code')
        registration.status = 'completed'
        registration.save()

        # Create user account and other setup can happen here
        # For now, just mark as completed

        return JsonResponse({
            'success': True,
            'message': 'Registro completado exitosamente',
            'registration_id': registration.id
        })

    except SubscriptionRegistration.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Registro no encontrado'
        }, status=404)

    except Exception as e:
        logger.error(f"Error completing business registration: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Error interno del servidor'
        }, status=500)