from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
import json
import logging

from .models import User, Business, UserSession, BusinessSettings
from .forms import LoginForm, RegisterBusinessForm, RegisterUserForm

logger = logging.getLogger(__name__)


class LoginView(View):
    """Vista de login personalizada"""
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('pos:punto_de_venta')
        
        form = LoginForm()
        return render(request, 'accounts/login.html', {'form': form})
    
    def post(self, request):
        form = LoginForm(request.POST)
        
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                # Verificar que el negocio tenga suscripción activa
                if not user.business.is_subscription_active:
                    messages.error(request, 'La suscripción de tu negocio ha expirado. Contacta al administrador.')
                    return render(request, 'accounts/login.html', {'form': form})
                
                # Verificar límite de usuarios simultáneos
                if self._verificar_limite_usuarios(user):
                    login(request, user)
                    messages.success(request, f'Bienvenido, {user.get_full_name() or user.username}!')
                    return redirect('pos:punto_de_venta')
                else:
                    messages.error(
                        request, 
                        f'Se ha alcanzado el límite de {user.business.max_concurrent_users} usuarios simultáneos. '
                        'Intenta más tarde o contacta al administrador para ampliar tu plan.'
                    )
            else:
                messages.error(request, 'Usuario o contraseña incorrectos.')
        
        return render(request, 'accounts/login.html', {'form': form})
    
    def _verificar_limite_usuarios(self, user):
        """Verifica si el usuario puede conectarse según el límite"""
        # Limpiar sesiones inactivas
        cutoff_time = timezone.now() - timezone.timedelta(minutes=30)
        UserSession.objects.filter(
            user__business=user.business,
            last_activity__lt=cutoff_time
        ).delete()
        
        # Contar sesiones activas
        sesiones_activas = UserSession.objects.filter(
            user__business=user.business,
            last_activity__gte=cutoff_time
        ).count()
        
        return sesiones_activas < user.business.max_concurrent_users


class LogoutView(View):
    """Vista de logout personalizada"""
    
    def get(self, request):
        return self.post(request)
    
    def post(self, request):
        if request.user.is_authenticated:
            # Limpiar sesión de UserSession
            session_key = request.session.session_key
            if session_key:
                UserSession.objects.filter(
                    user=request.user,
                    session_key=session_key
                ).delete()
            
            user_name = request.user.get_full_name() or request.user.username
            logout(request)
            messages.success(request, f'Hasta luego, {user_name}!')
        
        return redirect('accounts:login')


class RegisterBusinessView(View):
    """Vista para registrar un nuevo negocio"""
    
    def get(self, request):
        business_form = RegisterBusinessForm()
        user_form = RegisterUserForm()
        
        context = {
            'business_form': business_form,
            'user_form': user_form
        }
        return render(request, 'accounts/register.html', context)
    
    def post(self, request):
        business_form = RegisterBusinessForm(request.POST)
        user_form = RegisterUserForm(request.POST)
        
        if business_form.is_valid() and user_form.is_valid():
            try:
                with transaction.atomic():
                    # Crear el negocio
                    business = business_form.save()
                    
                    # Crear configuraciones del negocio
                    BusinessSettings.objects.create(
                        business=business,
                        enable_custom_rounding=True,
                        send_daily_reports=False,
                        show_low_stock_alerts=True
                    )
                    
                    # Crear el usuario propietario
                    user = user_form.save(commit=False)
                    user.business = business
                    user.is_business_owner = True
                    user.save()
                    
                    # Login automático
                    login(request, user)
                    
                    messages.success(
                        request, 
                        f'¡Bienvenido! Tu negocio "{business.name}" ha sido registrado exitosamente. '
                        'Tienes acceso al plan básico.'
                    )
                    
                    return redirect('pos:punto_de_venta')
                    
            except Exception as e:
                logger.error(f"Error registrando negocio: {e}")
                messages.error(request, 'Ocurrió un error al registrar el negocio. Intenta nuevamente.')
        
        context = {
            'business_form': business_form,
            'user_form': user_form
        }
        return render(request, 'accounts/register.html', context)


@method_decorator(login_required, name='dispatch')
class DashboardView(View):
    """Dashboard principal del negocio"""
    
    def get(self, request):
        business = request.user.business
        
        # Estadísticas básicas
        from pos.utils import calcular_estadisticas_ventas, obtener_productos_stock_bajo, obtener_usuario_activos_negocio
        
        # Stats del día
        stats_hoy = calcular_estadisticas_ventas(business)
        
        # Stats del mes
        inicio_mes = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        fin_mes = timezone.now()
        stats_mes = calcular_estadisticas_ventas(business, inicio_mes, fin_mes)
        
        # Productos con stock bajo
        productos_bajo_stock = obtener_productos_stock_bajo(business)
        
        # Usuarios activos
        usuarios_activos = obtener_usuario_activos_negocio(business)
        
        context = {
            'business': business,
            'stats_hoy': stats_hoy,
            'stats_mes': stats_mes,
            'productos_bajo_stock': productos_bajo_stock[:5],  # Solo los primeros 5
            'usuarios_activos': usuarios_activos,
            'total_productos_bajo_stock': len(productos_bajo_stock),
            'plan_info': {
                'nombre': business.get_plan_display(),
                'usuarios_permitidos': business.max_concurrent_users,
                'costo_mensual': business.monthly_cost,
                'usuarios_conectados': len(usuarios_activos)
            }
        }
        
        return render(request, 'accounts/dashboard.html', context)


@method_decorator(login_required, name='dispatch')
class ConfiguracionView(View):
    """Vista para configurar el negocio"""
    
    def get(self, request):
        business = request.user.business
        
        # Solo el propietario puede ver configuraciones
        if not request.user.is_business_owner:
            messages.error(request, 'No tienes permisos para acceder a la configuración.')
            return redirect('pos:punto_de_venta')
        
        context = {
            'business': business,
            'settings': business.settings if hasattr(business, 'settings') else None
        }
        
        return render(request, 'accounts/configuracion.html', context)
    
    def post(self, request):
        if not request.user.is_business_owner:
            messages.error(request, 'No tienes permisos para modificar la configuración.')
            return redirect('pos:punto_de_venta')
        
        business = request.user.business
        
        try:
            # Actualizar configuraciones del negocio
            business.name = request.POST.get('business_name', business.name)
            business.email = request.POST.get('business_email', business.email)
            business.phone = request.POST.get('business_phone', business.phone)
            business.address = request.POST.get('business_address', business.address)
            business.save()
            
            # Actualizar configuraciones específicas
            settings_obj, created = BusinessSettings.objects.get_or_create(business=business)
            settings_obj.enable_custom_rounding = request.POST.get('enable_custom_rounding') == 'on'
            settings_obj.send_daily_reports = request.POST.get('send_daily_reports') == 'on'
            settings_obj.report_email = request.POST.get('report_email', '')
            settings_obj.show_low_stock_alerts = request.POST.get('show_low_stock_alerts') == 'on'
            settings_obj.save()
            
            messages.success(request, 'Configuración actualizada exitosamente.')
            
        except Exception as e:
            logger.error(f"Error actualizando configuración: {e}")
            messages.error(request, 'Error al actualizar la configuración.')
        
        return redirect('accounts:configuracion')


@method_decorator(login_required, name='dispatch')
class UsuariosActivosView(View):
    """API para obtener usuarios activos en tiempo real"""
    
    def get(self, request):
        try:
            from pos.utils import obtener_usuario_activos_negocio
            
            usuarios_activos = obtener_usuario_activos_negocio(request.user.business)
            
            # Formatear datos para JSON
            usuarios_data = []
            for usuario in usuarios_activos:
                usuarios_data.append({
                    'username': usuario['username'],
                    'nombre_completo': usuario['nombre_completo'],
                    'ultima_actividad': usuario['ultima_actividad'].strftime('%H:%M:%S'),
                    'ip_address': usuario['ip_address'],
                    'tiempo_conectado': str(usuario['tiempo_activo']).split('.')[0]  # Sin microsegundos
                })
            
            return JsonResponse({
                'usuarios_activos': usuarios_data,
                'total_conectados': len(usuarios_data),
                'limite_usuarios': request.user.business.max_concurrent_users
            })
            
        except Exception as e:
            logger.error(f"Error obteniendo usuarios activos: {e}")
            return JsonResponse({'error': 'Error interno del servidor'}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(login_required, name='dispatch')
class CerrarSesionUsuarioView(View):
    """API para que el propietario cierre sesiones de otros usuarios"""
    
    def post(self, request):
        if not request.user.is_business_owner:
            return JsonResponse({'error': 'Sin permisos'}, status=403)
        
        try:
            data = json.loads(request.body)
            username = data.get('username')
            
            if not username:
                return JsonResponse({'error': 'Username requerido'}, status=400)
            
            # Buscar el usuario en el mismo negocio
            usuario_a_cerrar = User.objects.filter(
                business=request.user.business,
                username=username
            ).first()
            
            if not usuario_a_cerrar:
                return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
            
            if usuario_a_cerrar == request.user:
                return JsonResponse({'error': 'No puedes cerrar tu propia sesión'}, status=400)
            
            # Cerrar todas las sesiones del usuario
            sesiones_cerradas = UserSession.objects.filter(user=usuario_a_cerrar).delete()
            
            return JsonResponse({
                'mensaje': f'Sesión de {username} cerrada exitosamente',
                'sesiones_cerradas': sesiones_cerradas[0]
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)
        except Exception as e:
            logger.error(f"Error cerrando sesión de usuario: {e}")
            return JsonResponse({'error': 'Error interno del servidor'}, status=500)