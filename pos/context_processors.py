"""
Context processors para POS Dulcería México
Maneja demo limitations, business context y configuraciones globales
"""

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import hashlib

def get_client_ip(request):
    """Obtener IP real del cliente (considerando proxies)"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def demo_context(request):
    """
    Context processor para manejar limitaciones del demo
    Persiste por IP para evitar refresh abuse
    """
    
    # Solo aplicar en páginas de demo
    if not request.path.startswith('/') or request.user.is_authenticated:
        return {}
    
    ip = get_client_ip(request)
    ip_hash = hashlib.md5(ip.encode()).hexdigest()[:8]  # Hash corto para cache key
    
    # Keys de cache por IP
    intentos_key = f"demo_intentos_{ip_hash}"
    carrito_key = f"demo_carrito_{ip_hash}"
    primera_visita_key = f"demo_primera_{ip_hash}"
    
    # Configuración del demo
    MAX_INTENTOS = 5
    MAX_PRODUCTOS_CARRITO = 3
    CACHE_TIMEOUT = 3600 * 24  # 24 horas
    
    # Verificar si es primera visita del día
    hoy = timezone.now().date().isoformat()
    primera_visita_hoy = cache.get(f"{primera_visita_key}_{hoy}")
    
    if not primera_visita_hoy:
        # Reset intentos para nueva visita del día
        cache.set(intentos_key, MAX_INTENTOS, CACHE_TIMEOUT)
        cache.set(carrito_key, [], CACHE_TIMEOUT)
        cache.set(f"{primera_visita_key}_{hoy}", True, CACHE_TIMEOUT)
    
    # Obtener estado actual
    intentos_restantes = cache.get(intentos_key, MAX_INTENTOS)
    carrito_demo = cache.get(carrito_key, [])
    
    # Calcular productos en carrito (cantidad total)
    productos_en_carrito = sum(item.get('cantidad', 1) for item in carrito_demo)
    
    # Estado del demo
    demo_agotado = intentos_restantes <= 0 or productos_en_carrito >= MAX_PRODUCTOS_CARRITO
    
    return {
        'DEMO_INTENTOS_RESTANTES': intentos_restantes,
        'DEMO_MAX_INTENTOS': MAX_INTENTOS,
        'DEMO_CARRITO': carrito_demo,
        'DEMO_PRODUCTOS_EN_CARRITO': productos_en_carrito,
        'DEMO_MAX_PRODUCTOS': MAX_PRODUCTOS_CARRITO,
        'DEMO_AGOTADO': demo_agotado,
        'DEMO_IP_HASH': ip_hash,  # Para JavaScript
        'ES_DEMO': True,
    }

def business_context(request):
    """
    Context processor para información del negocio del usuario
    """
    context = {}
    
    if request.user.is_authenticated and hasattr(request.user, 'business'):
        business = request.user.business
        
        if business:
            # Información básica del negocio
            context.update({
                'BUSINESS': business,
                'BUSINESS_NOMBRE': business.nombre,
                'BUSINESS_PLAN': business.plan_actual,
                'BUSINESS_ACTIVO': business.esta_activo(),
                'BUSINESS_DIAS_RESTANTES': business.dias_restantes(),
            })
            
            # Límites según el plan
            context.update({
                'MAX_USUARIOS': business.max_usuarios,
                'MAX_PRODUCTOS': business.max_productos,
                'MAX_SUCURSALES': business.max_sucursales,
                'USUARIOS_DISPONIBLES': business.usuarios_disponibles(),
                'PRODUCTOS_DISPONIBLES': business.productos_disponibles(),
            })
            
            # Funcionalidades habilitadas
            context.update({
                'TIENE_LECTOR_CODIGOS': business.tiene_lector_codigos,
                'TIENE_ALERTAS_STOCK': business.tiene_alertas_stock,
                'TIENE_TICKETS': business.tiene_tickets,
                'TIENE_CONTROL_CAJAS': business.tiene_control_cajas,
                'TIENE_DASHBOARD': business.tiene_dashboard,
                'TIENE_SOPORTE_PRIORITARIO': business.tiene_soporte_prioritario,
                'DIAS_HISTORIAL_VENTAS': business.dias_historial_ventas,
            })
            
            # Sucursal activa del usuario
            if hasattr(request.user, 'sucursal_asignada') and request.user.sucursal_asignada:
                context['SUCURSAL_ACTIVA'] = request.user.sucursal_asignada
            elif hasattr(request.user, 'sucursal_preferida') and request.user.sucursal_preferida:
                context['SUCURSAL_ACTIVA'] = request.user.sucursal_preferida
            else:
                # Usar sucursal principal del negocio
                sucursal_principal = business.sucursales.filter(es_principal=True).first()
                if sucursal_principal:
                    context['SUCURSAL_ACTIVA'] = sucursal_principal
                else:
                    context['SUCURSAL_ACTIVA'] = business.sucursales.first()
    
    return context

def pos_settings_context(request):
    """
    Context processor para configuraciones generales del POS
    """
    return {
        'POS_SETTINGS': getattr(settings, 'POS_SETTINGS', {}),
        'PLANES_DISPONIBLES': getattr(settings, 'PLANES_SUSCRIPCION', {}),
        'MONEDA_SIMBOLO': '$',
        'FECHA_ACTUAL': timezone.now(),
        'TIMEZONE_USUARIO': 'America/Mexico_City',
    }

def navigation_context(request):
    """
    Context processor para navegación y menús
    """
    path = request.path
    
    # Determinar sección activa
    seccion_activa = 'demo'
    if '/pos/' in path:
        seccion_activa = 'pos'
    elif '/inventario/' in path:
        seccion_activa = 'inventario'
    elif '/reportes/' in path:
        seccion_activa = 'reportes'
    elif '/configuracion/' in path:
        seccion_activa = 'configuracion'
    
    # Menú de navegación según usuario
    menu_items = []
    
    if request.user.is_authenticated:
        # Menú para usuarios autenticados
        menu_items = [
            {
                'nombre': 'POS',
                'url': '/pos/',
                'icono': 'shopping-cart',
                'activo': seccion_activa == 'pos',
                'permiso': True
            },
            {
                'nombre': 'Inventario',
                'url': '/inventario/',
                'icono': 'package',
                'activo': seccion_activa == 'inventario',
                'permiso': request.user.puede_agregar_productos or request.user.puede_editar_productos
            },
            {
                'nombre': 'Reportes',
                'url': '/reportes/',
                'icono': 'bar-chart',
                'activo': seccion_activa == 'reportes',
                'permiso': request.user.puede_ver_reportes or request.user.es_propietario()
            },
            {
                'nombre': 'Configuración',
                'url': '/configuracion/',
                'icono': 'settings',
                'activo': seccion_activa == 'configuracion',
                'permiso': request.user.es_propietario()
            },
        ]
    else:
        # Menú para demo público
        menu_items = [
            {
                'nombre': 'Demo',
                'url': '/',
                'icono': 'play',
                'activo': seccion_activa == 'demo',
                'permiso': True
            },
            {
                'nombre': 'Planes',
                'url': '/planes/',
                'icono': 'star',
                'activo': seccion_activa == 'planes',
                'permiso': True
            },
            {
                'nombre': 'Iniciar Sesión',
                'url': '/accounts/login/',
                'icono': 'log-in',
                'activo': seccion_activa == 'login',
                'permiso': True
            },
        ]
    
    # Filtrar por permisos
    menu_filtrado = [item for item in menu_items if item['permiso']]
    
    return {
        'SECCION_ACTIVA': seccion_activa,
        'MENU_ITEMS': menu_filtrado,
        'ES_PAGINA_DEMO': not request.user.is_authenticated,
        'RUTA_ACTUAL': path,
    }

def alerts_context(request):
    """
    Context processor para alertas y notificaciones
    """
    alerts = []
    
    if request.user.is_authenticated and hasattr(request.user, 'business'):
        business = request.user.business
        
        if business and business.esta_activo():
            # Alerta de vencimiento próximo
            dias_restantes = business.dias_restantes()
            if dias_restantes <= 7:
                alerts.append({
                    'tipo': 'warning' if dias_restantes > 3 else 'danger',
                    'mensaje': f'Tu suscripción vence en {dias_restantes} días',
                    'accion': '/planes/',
                    'accion_texto': 'Renovar Ahora'
                })
            
            # Alerta de límites alcanzados
            if business.productos_disponibles() <= 5:
                alerts.append({
                    'tipo': 'warning',
                    'mensaje': f'Solo puedes agregar {business.productos_disponibles()} productos más',
                    'accion': '/planes/',
                    'accion_texto': 'Upgrade Plan'
                })
            
            # Verificar productos con poco stock (solo si tiene la funcionalidad)
            if business.tiene_alertas_stock:
                try:
                    from pos.models import Producto
                    productos_bajo_stock = Producto.objects.filter(
                        business=business,
                        stock__lt=models.F('stock_minimo')
                    ).count()
                    
                    if productos_bajo_stock > 0:
                        alerts.append({
                            'tipo': 'info',
                            'mensaje': f'{productos_bajo_stock} productos con stock bajo',
                            'accion': '/inventario/',
                            'accion_texto': 'Ver Inventario'
                        })
                except:
                    pass
        
        elif business and not business.esta_activo():
            # Suscripción vencida
            alerts.append({
                'tipo': 'danger',
                'mensaje': 'Tu suscripción ha vencido. Renueva para seguir usando el sistema',
                'accion': '/planes/',
                'accion_texto': 'Renovar Ahora'
            })
    
    return {
        'ALERTS': alerts,
        'TIENE_ALERTAS': len(alerts) > 0,
    }

# Función helper para usar en JavaScript
def consumir_intento_demo(request):
    """
    Función para consumir un intento del demo desde las vistas
    """
    if request.user.is_authenticated:
        return True  # Usuarios autenticados no tienen límites
    
    ip = get_client_ip(request)
    ip_hash = hashlib.md5(ip.encode()).hexdigest()[:8]
    intentos_key = f"demo_intentos_{ip_hash}"
    
    intentos_actuales = cache.get(intentos_key, 5)
    
    if intentos_actuales <= 0:
        return False
    
    cache.set(intentos_key, intentos_actuales - 1, 3600 * 24)
    return True

def agregar_producto_carrito_demo(request, producto_data):
    """
    Función para agregar producto al carrito demo
    """
    if request.user.is_authenticated:
        return True  # Usuarios autenticados usan carrito real
    
    ip = get_client_ip(request)
    ip_hash = hashlib.md5(ip.encode()).hexdigest()[:8]
    carrito_key = f"demo_carrito_{ip_hash}"
    
    carrito_actual = cache.get(carrito_key, [])
    
    # Verificar límite de productos totales
    productos_totales = sum(item.get('cantidad', 1) for item in carrito_actual)
    nueva_cantidad = producto_data.get('cantidad', 1)
    
    if productos_totales + nueva_cantidad > 3:
        return False  # Límite alcanzado
    
    # Agregar/actualizar producto
    producto_existente = None
    for item in carrito_actual:
        if item.get('codigo') == producto_data.get('codigo'):
            producto_existente = item
            break
    
    if producto_existente:
        producto_existente['cantidad'] += nueva_cantidad
    else:
        carrito_actual.append(producto_data)
    
    cache.set(carrito_key, carrito_actual, 3600 * 24)
    return True