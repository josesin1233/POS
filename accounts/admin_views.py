from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import Business, UserPermissions, BusinessSettings
from .forms import UserPermissionsForm, CreateUserForm
import json
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

def require_business_owner(view_func):
    """Decorator para requerir que el usuario sea propietario del negocio"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Debes iniciar sesión.')
            return redirect('accounts:login')
        
        if not request.user.is_business_owner:
            messages.error(request, 'Solo los propietarios pueden acceder a esta sección.')
            return redirect('pos:punto_de_venta')
        
        if not hasattr(request.user, 'business') or not request.user.business:
            messages.error(request, 'No tienes un negocio asociado.')
            return redirect('pos:punto_de_venta')
            
        return view_func(request, *args, **kwargs)
    return wrapper

@login_required
@require_business_owner
def admin_dashboard(request):
    """Panel principal de administración"""
    business = request.user.business
    
    # Estadísticas básicas
    total_users = User.objects.filter(business=business).count()
    active_users = User.objects.filter(business=business, is_active=True).count()
    owners = User.objects.filter(business=business, is_business_owner=True).count()
    
    # Usuarios recientes
    recent_users = User.objects.filter(business=business).order_by('-date_joined')[:5]
    
    context = {
        'business': business,
        'total_users': total_users,
        'active_users': active_users,
        'owners': owners,
        'recent_users': recent_users,
    }
    
    return render(request, 'accounts/admin/dashboard.html', context)

@login_required
@require_business_owner
def user_management(request):
    """Gestión de usuarios del negocio"""
    business = request.user.business
    
    # Obtener todos los usuarios del negocio
    users = User.objects.filter(business=business).select_related('permissions').order_by('username')
    
    # Preparar datos de usuarios con sus permisos
    users_data = []
    for user in users:
        try:
            permissions = user.permissions
        except UserPermissions.DoesNotExist:
            # Crear permisos por defecto si no existen
            permissions = UserPermissions.create_default_permissions(
                user=user, 
                business=business, 
                is_owner=user.is_business_owner
            )
        
        users_data.append({
            'user': user,
            'permissions': permissions,
            'is_current_user': user == request.user
        })
    
    context = {
        'business': business,
        'users_data': users_data,
    }
    
    return render(request, 'accounts/admin/user_management.html', context)

@login_required
@require_business_owner
def edit_user_permissions(request, user_id):
    """Editar permisos de un usuario específico"""
    business = request.user.business
    user = get_object_or_404(User, id=user_id, business=business)
    
    # No permitir editar los permisos del propio usuario si es el único owner
    if (user == request.user and user.is_business_owner and 
        User.objects.filter(business=business, is_business_owner=True).count() == 1):
        messages.error(request, 'No puedes editar tus propios permisos siendo el único propietario.')
        return redirect('accounts:user_management')
    
    # Obtener o crear permisos
    try:
        permissions = user.permissions
    except UserPermissions.DoesNotExist:
        permissions = UserPermissions.create_default_permissions(
            user=user, 
            business=business, 
            is_owner=user.is_business_owner
        )
    
    if request.method == 'POST':
        form = UserPermissionsForm(request.POST, instance=permissions)
        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                    
                    # Log de la acción
                    logger.info(f"User {request.user.username} updated permissions for {user.username}")
                    
                    messages.success(request, f'Permisos de {user.get_full_name() or user.username} actualizados correctamente.')
                    return redirect('accounts:user_management')
            except Exception as e:
                logger.error(f"Error updating user permissions: {e}")
                messages.error(request, 'Error al actualizar permisos. Intenta de nuevo.')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = UserPermissionsForm(instance=permissions)
    
    context = {
        'business': business,
        'target_user': user,
        'permissions': permissions,
        'form': form,
        'is_owner': user.is_business_owner,
    }
    
    return render(request, 'accounts/admin/edit_permissions.html', context)

@login_required
@require_business_owner
def create_user(request):
    """Crear un nuevo usuario para el negocio"""
    business = request.user.business
    
    # Verificar límite de usuarios
    current_users = User.objects.filter(business=business).count()
    if current_users >= business.max_concurrent_users:
        messages.error(request, f'Has alcanzado el límite de {business.max_concurrent_users} usuarios para tu plan.')
        return redirect('accounts:user_management')
    
    if request.method == 'POST':
        form = CreateUserForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Crear usuario
                    user = form.save(commit=False)
                    user.business = business
                    user.is_business_owner = form.cleaned_data.get('is_business_owner', False)
                    user.save()
                    
                    # Crear permisos por defecto
                    UserPermissions.create_default_permissions(
                        user=user,
                        business=business,
                        is_owner=user.is_business_owner
                    )
                    
                    logger.info(f"User {request.user.username} created new user {user.username}")
                    
                    messages.success(request, f'Usuario {user.username} creado correctamente.')
                    return redirect('accounts:edit_user_permissions', user_id=user.id)
                    
            except Exception as e:
                logger.error(f"Error creating user: {e}")
                messages.error(request, 'Error al crear usuario. Intenta de nuevo.')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = CreateUserForm()
    
    context = {
        'business': business,
        'form': form,
        'users_count': current_users,
        'max_users': business.max_concurrent_users,
    }
    
    return render(request, 'accounts/admin/create_user.html', context)

@require_POST
@login_required
@require_business_owner
def toggle_user_active(request, user_id):
    """Activar/desactivar un usuario"""
    business = request.user.business
    user = get_object_or_404(User, id=user_id, business=business)
    
    # No permitir desactivar al propio usuario
    if user == request.user:
        return JsonResponse({'error': 'No puedes desactivar tu propia cuenta.'}, status=400)
    
    # No permitir desactivar al único owner
    if (user.is_business_owner and not user.is_active and
        User.objects.filter(business=business, is_business_owner=True, is_active=True).count() <= 1):
        return JsonResponse({'error': 'Debe haber al menos un propietario activo.'}, status=400)
    
    try:
        user.is_active = not user.is_active
        user.save()
        
        action = 'activado' if user.is_active else 'desactivado'
        logger.info(f"User {request.user.username} {action} user {user.username}")
        
        return JsonResponse({
            'success': True,
            'is_active': user.is_active,
            'message': f'Usuario {action} correctamente.'
        })
        
    except Exception as e:
        logger.error(f"Error toggling user active status: {e}")
        return JsonResponse({'error': 'Error al cambiar estado del usuario.'}, status=500)

@require_POST
@login_required
@require_business_owner
def delete_user(request, user_id):
    """Eliminar un usuario del negocio"""
    business = request.user.business
    user = get_object_or_404(User, id=user_id, business=business)
    
    # No permitir eliminar al propio usuario
    if user == request.user:
        return JsonResponse({'error': 'No puedes eliminar tu propia cuenta.'}, status=400)
    
    # No permitir eliminar al único owner
    if (user.is_business_owner and
        User.objects.filter(business=business, is_business_owner=True).count() <= 1):
        return JsonResponse({'error': 'Debe haber al menos un propietario.'}, status=400)
    
    try:
        username = user.username
        user.delete()
        
        logger.info(f"User {request.user.username} deleted user {username}")
        
        return JsonResponse({
            'success': True,
            'message': f'Usuario {username} eliminado correctamente.'
        })
        
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return JsonResponse({'error': 'Error al eliminar usuario.'}, status=500)

@login_required
@require_business_owner
def business_settings(request):
    """Configuraciones del negocio"""
    business = request.user.business
    
    # Obtener o crear configuraciones
    try:
        settings = business.settings
    except BusinessSettings.DoesNotExist:
        settings = BusinessSettings.objects.create(business=business)
    
    if request.method == 'POST':
        # Procesar formulario de configuraciones
        try:
            # Actualizar configuraciones básicas
            if 'show_low_stock_alerts' in request.POST:
                settings.show_low_stock_alerts = request.POST.get('show_low_stock_alerts') == 'on'
            
            if 'low_stock_threshold' in request.POST:
                settings.low_stock_threshold = int(request.POST.get('low_stock_threshold', 5))
            
            if 'enable_custom_rounding' in request.POST:
                settings.enable_custom_rounding = request.POST.get('enable_custom_rounding') == 'on'
            
            if 'send_daily_reports' in request.POST:
                settings.send_daily_reports = request.POST.get('send_daily_reports') == 'on'
            
            if 'report_email' in request.POST:
                settings.report_email = request.POST.get('report_email', '')
            
            settings.save()
            
            logger.info(f"User {request.user.username} updated business settings")
            messages.success(request, 'Configuraciones actualizadas correctamente.')
            
        except Exception as e:
            logger.error(f"Error updating business settings: {e}")
            messages.error(request, 'Error al actualizar configuraciones.')
    
    context = {
        'business': business,
        'settings': settings,
    }
    
    return render(request, 'accounts/admin/business_settings.html', context)

@login_required
def check_permission(request, permission_name):
    """API endpoint para verificar permisos de usuario"""
    if not request.user.is_authenticated:
        return JsonResponse({'has_permission': False, 'error': 'Not authenticated'})
    
    try:
        permissions = request.user.permissions
        has_permission = getattr(permissions, permission_name, False)
        
        return JsonResponse({
            'has_permission': has_permission,
            'user': request.user.username,
            'permission': permission_name
        })
        
    except UserPermissions.DoesNotExist:
        return JsonResponse({'has_permission': False, 'error': 'No permissions found'})
    except AttributeError:
        return JsonResponse({'has_permission': False, 'error': 'Invalid permission name'})
    except Exception as e:
        logger.error(f"Error checking permission {permission_name} for user {request.user.username}: {e}")
        return JsonResponse({'has_permission': False, 'error': 'Internal error'})