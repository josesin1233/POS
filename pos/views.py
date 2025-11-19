from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.conf import settings
from pos.models import Producto, Venta, VentaDetalle, Caja, GastoCaja, Sucursal, MovimientoStock
from accounts.models import Business, User
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import re 
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Sum, Count
from django.core.paginator import Paginator


logger = logging.getLogger(__name__)

# ========================
# UTILITY FUNCTIONS
# ========================

def get_client_ip(request):
    """Obtener la IP del cliente para registros de trazabilidad"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

# ========================
# VIEWS PRINCIPALES
# ========================

def index_view(request):
    """Vista principal - Demo público SIN login"""
    try:
        # Productos demo para mostrar en la página
        productos_demo = [
            {
                'codigo': '7501055304745',
                'nombre': 'Coca Cola 3L',
                'precio': 44.00,
                'stock': 15
            },
            {
                'codigo': '7501055333844',
                'nombre': 'Del Valle 1L', 
                'precio': 77.00,
                'stock': 12
            },
            {
                'codigo': '7501001116501',
                'nombre': 'Coca Cola Lata 355ml',
                'precio': 15.00,
                'stock': 25
            },
            {
                'codigo': '7501001100049',
                'nombre': 'Bonafont 1.5L',
                'precio': 18.00,
                'stock': 20
            }
        ]
        
        context = {
            'productos_demo': productos_demo,
            'es_demo': True,
            'intentos_maximos': 10,
            'productos_maximos': 4
        }
        
        return render(request, 'landing_page.html', context)
        
    except Exception as e:
        logger.error(f"Error en index_view: {e}")
        return render(request, 'landing_page.html', {
            'error': 'Error cargando demo',
            'productos_demo': []
        })

@login_required
def pos_view(request):
    """Vista POS completa - Solo usuarios autenticados"""
    try:
        # Verificar business del usuario con logging mejorado
        if not hasattr(request.user, 'business'):
            logger.warning(f"Usuario {request.user.username} no tiene atributo business")
            return redirect('accounts:register')
        
        if not request.user.business:
            logger.warning(f"Usuario {request.user.username} tiene business = None")
            return redirect('accounts:register')
        
        business = request.user.business
        logger.info(f"Usuario {request.user.username} accediendo con business: {business.name}")
        
        productos = Producto.objects.filter(business=business).order_by('nombre')
        
        context = {
            'productos': productos,
            'business': business,
            'es_demo': False,
            'user': request.user
        }
        
        return render(request, 'pos/pos.html', context)
        
    except Exception as e:
        logger.error(f"Error en pos_view para usuario {request.user.username}: {e}")
        return render(request, 'pos/pos.html', {
            'error': str(e),
            'productos': []
        })

# ========================
# API BUSINESS INFO
# ========================

@login_required
@require_http_methods(["GET"])
def get_business_info(request):
    """API para obtener información del negocio del usuario autenticado"""
    try:
        if not hasattr(request.user, 'business') or not request.user.business:
            return JsonResponse({'error': 'No business found for user'}, status=404)
        
        business = request.user.business
        return JsonResponse({
            'id': business.id,
            'name': business.name,
            'success': True
        })
    except Exception as e:
        logger.error(f"Error en get_business_info: {e}")
        return JsonResponse({'error': str(e)}, status=500)

# ========================
# API PRODUCTOS REAL
# ========================

@csrf_exempt
@require_http_methods(["POST"])
def buscar_producto(request):
    """API para búsqueda de productos - REQUIERE autenticación"""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Autenticación requerida'}, status=401)
        
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        
        if not query:
            return JsonResponse({'error': 'Query requerido'}, status=400)
        
        # Buscar en productos del business del usuario
        business = request.user.business
        if not business:
            return JsonResponse({'error': 'Business no configurado'}, status=400)
        
        # Intentar múltiples variaciones del código para compatibilidad
        variaciones = [
            re.sub(r'^0+', '', query),  
            '0' + query,  # Con cero inicial
            query.zfill(13),  # EAN-13 completo
            query.zfill(12)   # UPC-12 completo
        ]
        
        producto = None
        
        # Buscar por código con variaciones
        for variacion in variaciones:
            try:
                producto = Producto.objects.get(
                    business=business,
                    codigo=variacion
                )
                break
            except Producto.DoesNotExist:
                continue
        
        # Si no se encontró por código, buscar por nombre
        if not producto and len(query) >= 3:
            try:
                producto = Producto.objects.filter(
                    business=business,
                    nombre__icontains=query
                ).first()
            except:
                pass
        
        if not producto:
            return JsonResponse({'error': 'Producto no encontrado'}, status=404)
        
        return JsonResponse({
            'codigo': producto.codigo,
            'nombre': producto.nombre,
            'precio': float(producto.precio),
            'stock': producto.stock,
            'stock_minimo': producto.stock_minimo or 10
        })
        
    except Exception as e:
        logger.error(f"Error en buscar_producto: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def buscar_productos_sugerencias(request):
    """API para búsqueda inteligente con sugerencias múltiples - REQUIERE autenticación"""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Autenticación requerida'}, status=401)
        
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        
        if not query or len(query) < 2:
            return JsonResponse([], safe=False)
        
        business = request.user.business
        if not business:
            return JsonResponse({'error': 'Business no configurado'}, status=400)
        
        # Búsqueda inteligente: por código, nombre y descripción
        sugerencias = []
        
        # Buscar por código (exacto y parcial)
        productos_codigo = Producto.objects.filter(
            business=business,
            codigo__icontains=query,
            activo=True
        )[:5]
        
        for producto in productos_codigo:
            sugerencias.append({
                'codigo': producto.codigo,
                'nombre': producto.nombre,
                'precio': float(producto.precio),
                'stock': producto.stock,
                'tipo_match': 'codigo'
            })
        
        # Buscar por nombre (sin duplicados)
        codigos_ya_agregados = [p['codigo'] for p in sugerencias]
        productos_nombre = Producto.objects.filter(
            business=business,
            nombre__icontains=query,
            activo=True
        ).exclude(codigo__in=codigos_ya_agregados)[:5]
        
        for producto in productos_nombre:
            sugerencias.append({
                'codigo': producto.codigo,
                'nombre': producto.nombre,
                'precio': float(producto.precio),
                'stock': producto.stock,
                'tipo_match': 'nombre'
            })
        
        # Buscar por descripción si hay campo
        if hasattr(Producto, 'descripcion') and len(sugerencias) < 10:
            codigos_ya_agregados = [p['codigo'] for p in sugerencias]
            productos_descripcion = Producto.objects.filter(
                business=business,
                descripcion__icontains=query,
                activo=True
            ).exclude(codigo__in=codigos_ya_agregados)[:3]
            
            for producto in productos_descripcion:
                sugerencias.append({
                    'codigo': producto.codigo,
                    'nombre': producto.nombre,
                    'precio': float(producto.precio),
                    'stock': producto.stock,
                    'tipo_match': 'descripcion'
                })
        
        return JsonResponse(sugerencias[:10], safe=False)  # Máximo 10 sugerencias
        
    except Exception as e:
        logger.error(f"Error en buscar_productos_sugerencias: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def agregar_carrito(request):
    """API para agregar al carrito real - REQUIERE autenticación"""
    try:
        logger.info(f"agregar_carrito: method={request.method}, user={request.user}, authenticated={request.user.is_authenticated}")

        if not request.user.is_authenticated:
            logger.warning("agregar_carrito: Usuario no autenticado")
            return JsonResponse({'error': 'Autenticación requerida'}, status=401)

        # Verificar que hay contenido en el body
        if not request.body:
            logger.warning("agregar_carrito: No hay datos en el body")
            return JsonResponse({'error': 'Datos requeridos'}, status=400)

        try:
            data = json.loads(request.body)
            logger.info(f"agregar_carrito: datos recibidos: {data}")
        except json.JSONDecodeError as e:
            logger.error(f"agregar_carrito: Error decodificando JSON: {e}")
            return JsonResponse({'error': 'JSON inválido'}, status=400)
        codigo = data.get('codigo', '').strip()
        cantidad = int(data.get('cantidad', 1))
        
        if not codigo or cantidad <= 0:
            return JsonResponse({'error': 'Datos inválidos'}, status=400)
        
        # Buscar producto
        business = request.user.business
        try:
            producto = Producto.objects.get(business=business, codigo=codigo)
        except Producto.DoesNotExist:
            return JsonResponse({'error': 'Producto no encontrado'}, status=404)
        
        # Verificar stock
        if producto.stock < cantidad:
            return JsonResponse({
                'error': f'Stock insuficiente. Disponible: {producto.stock}'
            }, status=400)
        
        precio_total = float(producto.precio) * cantidad
        
        return JsonResponse({
            'codigo': producto.codigo,
            'nombre': producto.nombre,
            'precio_unitario': float(producto.precio),
            'cantidad': cantidad,
            'precio_total': precio_total,
            'stock_disponible': producto.stock
        })
        
    except Exception as e:
        logger.error(f"Error en agregar_carrito: {e}")
        return JsonResponse({'error': str(e)}, status=500)

# ========================
# API VENTAS
# ========================

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def registrar_venta(request):
    """API para registrar venta completa"""
    try:
        data = json.loads(request.body)
        productos = data.get('productos', [])
        monto_pagado = Decimal(str(data.get('monto_pagado', 0)))
        
        if not productos:
            return JsonResponse({'error': 'No hay productos'}, status=400)
        
        business = request.user.business
        total_venta = Decimal('0')
        productos_venta = []
        
        # Validar productos y calcular total
        for item in productos:
            codigo = item.get('codigo')
            cantidad = int(item.get('cantidad', 1))
            
            try:
                producto = Producto.objects.get(business=business, codigo=codigo)
            except Producto.DoesNotExist:
                return JsonResponse({
                    'error': f'Producto {codigo} no encontrado'
                }, status=404)
            
            if producto.stock < cantidad:
                return JsonResponse({
                    'error': f'Stock insuficiente para {producto.nombre}'
                }, status=400)
            
            subtotal = producto.precio * cantidad
            total_venta += subtotal
            
            productos_venta.append({
                'producto': producto,
                'cantidad': cantidad,
                'precio_unitario': producto.precio,
                'subtotal': subtotal
            })
        
        # Verificar pago
        if monto_pagado < total_venta:
            return JsonResponse({'error': 'Pago insuficiente'}, status=400)
        
        # Obtener o crear sucursal principal
        sucursal = business.sucursales.filter(es_principal=True).first()
        if not sucursal:
            # Crear sucursal principal si no existe
            from .models import Sucursal
            sucursal = Sucursal.objects.create(
                business=business,
                nombre="Sucursal Principal",
                es_principal=True,
                activa=True
            )
        
        # Crear venta
        venta = Venta.objects.create(
            business=business,
            sucursal=sucursal,
            usuario=request.user,
            subtotal=total_venta,
            total=total_venta,
            monto_pagado=monto_pagado,
            cambio=monto_pagado - total_venta,
            metodo_pago='efectivo'  # Default, could be enhanced later
        )
        
        # Crear detalles y actualizar stock CON REGISTRO DE MOVIMIENTOS
        for item in productos_venta:
            VentaDetalle.objects.create(
                venta=venta,
                producto=item['producto'],
                cantidad=item['cantidad'],
                precio_unitario=item['precio_unitario'],
                subtotal=item['subtotal']
            )

            # Registrar movimiento de stock ANTES de actualizar
            producto = item['producto']
            stock_anterior = producto.stock
            cantidad_vendida = item['cantidad']
            stock_nuevo = stock_anterior - cantidad_vendida

            # Crear registro de movimiento de stock
            MovimientoStock.objects.create(
                business=business,
                producto=producto,
                tipo_movimiento='venta',
                cantidad=-cantidad_vendida,  # Negativo porque es una salida
                stock_anterior=stock_anterior,
                stock_nuevo=stock_nuevo,
                venta=venta,
                usuario=request.user,
                motivo=f'Venta #{venta.folio} - {cantidad_vendida} unidades',
                ip_address=get_client_ip(request)
            )

            # Actualizar stock del producto
            producto.stock = stock_nuevo
            producto.save()
        
        return JsonResponse({
            'success': True,
            'venta_id': venta.id,
            'total': float(total_venta),
            'cambio': float(venta.cambio),
            'fecha': venta.fecha_creacion.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error registrando venta: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def total_dia_hoy(request):
    """API para obtener total de ventas del día"""
    try:
        # Check if user has a business
        if not hasattr(request.user, 'business') or not request.user.business:
            return JsonResponse({
                'total_hoy': 0.0,
                'ventas_count': 0,
                'fecha': datetime.now().date().isoformat(),
                'message': 'Usuario sin negocio asignado'
            })
        
        business = request.user.business
        hoy = datetime.now().date()
        
        ventas_hoy = Venta.objects.filter(
            business=business,
            fecha_creacion__date=hoy,
            estado='completada'  # Solo ventas completadas
        )
        
        total_hoy = sum(venta.total for venta in ventas_hoy)
        
        return JsonResponse({
            'total_hoy': float(total_hoy),
            'ventas_count': ventas_hoy.count(),
            'fecha': hoy.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error calculando total del día: {e}")
        return JsonResponse({
            'total_hoy': 0.0,
            'ventas_count': 0,
            'fecha': datetime.now().date().isoformat(),
            'error': str(e)
        }, status=500)

def ventas_api(request):
    """API para obtener historial de ventas con filtros"""
    try:
        # Check if user is authenticated
        if not request.user.is_authenticated:
            return JsonResponse({
                'error': 'Usuario no autenticado',
                'ventas': []
            }, status=401)
            
        if not hasattr(request.user, 'business'):
            return JsonResponse({
                'error': 'Usuario sin negocio asignado',
                'ventas': []
            }, status=400)
        
        business = request.user.business
        
        from datetime import timedelta
        from django.utils import timezone
        from django.db.models import Sum
        from zoneinfo import ZoneInfo

        # Obtener fecha actual en timezone de México
        mexico_tz = ZoneInfo('America/Mexico_City')
        ahora_mexico = timezone.now().astimezone(mexico_tz)
        hoy = ahora_mexico.date()

        # Obtener parámetros de filtro
        dia = request.GET.get('dia')
        mes = request.GET.get('mes')
        anio = request.GET.get('anio')

        # Calcular total del día actual siempre usando timezone local
        ventas_hoy = Venta.objects.filter(
            business=business,
            estado='completada',
            fecha_creacion__date=hoy
        )
        total_del_dia = ventas_hoy.aggregate(total=Sum('total'))['total'] or 0
        
        # Filtrar ventas para mostrar
        if dia:
            fecha = datetime.strptime(dia, '%Y-%m-%d').date()
            ventas_query = Venta.objects.filter(
                business=business,
                estado='completada',
                fecha_creacion__date=fecha
            ).order_by('-fecha_creacion')
        elif mes:
            año, mes_num = mes.split('-')
            ventas_query = Venta.objects.filter(
                business=business,
                estado='completada',
                fecha_creacion__year=int(año),
                fecha_creacion__month=int(mes_num)
            ).order_by('-fecha_creacion')
        elif anio:
            ventas_query = Venta.objects.filter(
                business=business,
                estado='completada',
                fecha_creacion__year=int(anio)
            ).order_by('-fecha_creacion')
        else:
            # Agrupar ventas por períodos
            ventas_query = Venta.objects.filter(
                business=business,
                estado='completada'
            ).order_by('-fecha_creacion')
            
            # Hoy
            ventas_hoy_list = list(ventas_query.filter(fecha_creacion__date=hoy))
            
            # Esta semana (últimos 7 días excluyendo hoy)
            hace_semana = hoy - timedelta(days=7)
            ayer = hoy - timedelta(days=1)
            ventas_semana = list(ventas_query.filter(
                fecha_creacion__date__gte=hace_semana,
                fecha_creacion__date__lte=ayer
            ))
            
            # Este mes (excluyendo la última semana)
            primer_dia_mes = hoy.replace(day=1)
            ventas_mes = list(ventas_query.filter(
                fecha_creacion__date__gte=primer_dia_mes,
                fecha_creacion__date__lt=hace_semana
            ))
            
            # Meses anteriores (últimos 6 meses)
            hace_6_meses = (hoy - timedelta(days=180)).replace(day=1)
            ventas_meses_anteriores = list(ventas_query.filter(
                fecha_creacion__date__gte=hace_6_meses,
                fecha_creacion__date__lt=primer_dia_mes
            ))
            
            # Función para convertir venta a diccionario
            def venta_to_dict(venta):
                return {
                    'id': venta.id,
                    'fecha_creacion': venta.fecha_creacion.isoformat(),
                    'total': float(venta.total),
                    'usuario': {
                        'username': venta.usuario.username,
                        'nombre_completo': f"{venta.usuario.first_name} {venta.usuario.last_name}".strip() or venta.usuario.username
                    },
                    'folio': venta.folio,
                    'metodo_pago': venta.get_metodo_pago_display(),
                    'detalles': [
                        {
                            'producto': {'nombre': detalle.producto.nombre},
                            'cantidad': detalle.cantidad,
                            'precio_unitario': float(detalle.precio_unitario)
                        }
                        for detalle in venta.detalles.all()
                    ],
                    'movimientos_stock': [
                        {
                            'producto': mov.producto.nombre,
                            'cantidad_movida': mov.cantidad,
                            'stock_anterior': mov.stock_anterior,
                            'stock_nuevo': mov.stock_nuevo
                        }
                        for mov in venta.movimientos_stock.all()
                    ] if hasattr(venta, 'movimientos_stock') else []
                }

            # Combinar todo con marcadores de grupo
            ventas_agrupadas = []
            
            if ventas_hoy_list:
                ventas_agrupadas.append({
                    'tipo': 'grupo',
                    'titulo': f'Hoy ({hoy.strftime("%d/%m/%Y")})',
                    'ventas': [venta_to_dict(v) for v in ventas_hoy_list],
                    'total_grupo': float(sum(v.total for v in ventas_hoy_list))
                })
                
            if ventas_semana:
                ventas_agrupadas.append({
                    'tipo': 'grupo',
                    'titulo': 'Esta semana',
                    'ventas': [venta_to_dict(v) for v in ventas_semana],
                    'total_grupo': float(sum(v.total for v in ventas_semana))
                })
                
            if ventas_mes:
                ventas_agrupadas.append({
                    'tipo': 'grupo',
                    'titulo': f'Este mes ({hoy.strftime("%B %Y")})',
                    'ventas': [venta_to_dict(v) for v in ventas_mes],
                    'total_grupo': float(sum(v.total for v in ventas_mes))
                })
                
            if ventas_meses_anteriores:
                ventas_agrupadas.append({
                    'tipo': 'grupo',
                    'titulo': 'Meses anteriores',
                    'ventas': [venta_to_dict(v) for v in ventas_meses_anteriores],
                    'total_grupo': float(sum(v.total for v in ventas_meses_anteriores))
                })
            
            # Retornar con total del día actual
            return JsonResponse({
                'grupos': ventas_agrupadas,
                'total_del_dia': float(total_del_dia),
                'es_agrupado': True
            }, safe=False)
        
        # Construir respuesta para filtros específicos
        ventas_data = []
        for venta in ventas_query:
            productos_venta = []
            for detalle in venta.detalles.all():
                productos_venta.append({
                    'nombre_producto': detalle.producto.nombre,
                    'cantidad_vendida': detalle.cantidad,
                    'precio_unitario': float(detalle.precio_unitario),
                    'total': float(detalle.cantidad * detalle.precio_unitario)
                })

            ventas_data.append({
                'id': venta.id,
                'fecha': venta.fecha_creacion.isoformat(),
                'total_venta': float(venta.total),
                'usuario': {
                    'username': venta.usuario.username,
                    'nombre_completo': f"{venta.usuario.first_name} {venta.usuario.last_name}".strip() or venta.usuario.username
                },
                'folio': venta.folio,
                'metodo_pago': venta.get_metodo_pago_display(),
                'productos': productos_venta,
                'movimientos_stock': [
                    {
                        'producto': mov.producto.nombre,
                        'cantidad_movida': mov.cantidad,
                        'stock_anterior': mov.stock_anterior,
                        'stock_nuevo': mov.stock_nuevo
                    }
                    for mov in venta.movimientos_stock.all()
                ] if hasattr(venta, 'movimientos_stock') else []
            })
        
        return JsonResponse({
            'ventas': ventas_data,
            'total_del_dia': float(total_del_dia),
            'es_agrupado': False
        }, safe=False)
        
    except Exception as e:
        logger.error(f"Error en ventas_api: {e}")
        return JsonResponse({
            'error': f'Error interno del servidor: {str(e)}',
            'ventas': []
        }, status=500)

# ========================
# VIEWS CAJA
# ========================

@csrf_exempt
def caja_estado_api(request):
    """API para obtener estado actual de la caja"""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Usuario no autenticado'}, status=401)
            
        if not hasattr(request.user, 'business'):
            return JsonResponse({'error': 'Usuario sin negocio asignado'}, status=400)
        
        # Verificar si los modelos existen
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_name = 'pos_caja';")
                if not cursor.fetchone():
                    return JsonResponse({'error': 'Tabla Caja no existe - ejecutar migraciones'}, status=500)
        except Exception as db_error:
            logger.error(f"Error verificando tabla: {db_error}")
            # Si falla la verificación, intentar continuar
        
        business = request.user.business
        hoy = timezone.now().date()
        
        # Buscar caja del día (con fallback si la tabla no existe)
        try:
            caja = Caja.objects.get(business=business, fecha_apertura__date=hoy)
            estado = 'abierta' if caja.estado == 'abierta' else 'cerrada'
            monto_actual = float(caja.monto_inicial)  # Usar monto_inicial por ahora
        except Caja.DoesNotExist:
            estado = 'cerrada'
            monto_actual = 0.0
            caja = None
        except Exception as caja_error:
            # Si falla por tabla no existente, devolver estado por defecto
            logger.error(f"Error accediendo a modelo Caja: {caja_error}")
            estado = 'cerrada'
            monto_actual = 0.0
            caja = None
        
        # Calcular ventas del día
        ventas_hoy = Venta.objects.filter(
            business=business,
            fecha_creacion__date=hoy,
            estado='completada'
        )
        total_ventas = ventas_hoy.aggregate(total=Sum('total'))['total'] or 0
        
        # Calcular gastos del día (con fallback si la tabla no existe)
        try:
            gastos_hoy = GastoCaja.objects.filter(
                business=business,
                fecha__date=hoy
            )
            total_gastos = gastos_hoy.aggregate(total=Sum('monto'))['total'] or 0
        except Exception as gastos_error:
            logger.error(f"Error accediendo a modelo GastoCaja: {gastos_error}")
            total_gastos = 0
        
        # Efectivo esperado = monto inicial + ventas - gastos
        efectivo_esperado = (caja.monto_inicial if caja else 0) + total_ventas - total_gastos
        
        return JsonResponse({
            'estado': estado,
            'monto_actual': monto_actual,
            'efectivo_esperado': float(efectivo_esperado),
            'total_gastos': float(total_gastos),
            'total_ventas': float(total_ventas)
        })
        
    except Exception as e:
        logger.error(f"Error en caja_estado_api: {e}")
        return JsonResponse({'error': f'Error interno: {str(e)}'}, status=500)

@csrf_exempt
def caja_abrir_api(request):
    """API para abrir caja con monto inicial"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
        
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Usuario no autenticado'}, status=401)
            
        if not hasattr(request.user, 'business'):
            return JsonResponse({'error': 'Usuario sin negocio asignado'}, status=400)
        
        import json
        data = json.loads(request.body)
        monto_inicial = data.get('monto_inicial', 0)
        
        if monto_inicial < 0:
            return JsonResponse({'error': 'El monto inicial no puede ser negativo'}, status=400)
        
        business = request.user.business
        hoy = timezone.now().date()
        
        # Verificar si ya existe una caja para hoy (con fallback si la tabla no existe)
        try:
            caja_existente = Caja.objects.filter(business=business, fecha_apertura__date=hoy).first()
            if caja_existente:
                return JsonResponse({'error': 'Ya existe una caja para el día de hoy'}, status=400)
        except Exception as caja_error:
            logger.error(f"Error verificando caja existente: {caja_error}")
            return JsonResponse({'error': 'Sistema de caja no disponible - ejecutar migraciones'}, status=500)
        
        # Obtener sucursal principal o crear una por defecto
        sucursal = business.sucursales.filter(es_principal=True).first()
        if not sucursal:
            sucursal = business.sucursales.first()
        if not sucursal:
            # Crear sucursal por defecto
            sucursal = Sucursal.objects.create(
                business=business,
                nombre="Principal",
                es_principal=True
            )
        
        # Crear nueva caja
        caja = Caja.objects.create(
            business=business,
            sucursal=sucursal,
            monto_inicial=monto_inicial,
            estado='abierta',
            usuario_apertura=request.user
        )
        
        return JsonResponse({'success': True, 'message': 'Caja abierta exitosamente'})
        
    except Exception as e:
        logger.error(f"Error en caja_abrir_api: {e}")
        return JsonResponse({'error': f'Error interno: {str(e)}'}, status=500)

@csrf_exempt
def caja_cerrar_api(request):
    """API para cerrar caja con conteo final"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
        
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Usuario no autenticado'}, status=401)
            
        if not hasattr(request.user, 'business'):
            return JsonResponse({'error': 'Usuario sin negocio asignado'}, status=400)
        
        import json
        data = json.loads(request.body)
        efectivo_real = data.get('efectivo_real', 0)
        
        business = request.user.business
        hoy = timezone.now().date()
        
        # Buscar caja del día
        try:
            caja = Caja.objects.get(business=business, fecha_apertura__date=hoy, estado='abierta')
        except Caja.DoesNotExist:
            return JsonResponse({'error': 'No hay una caja abierta para cerrar'}, status=400)
        
        # Calcular diferencia
        ventas_hoy = Venta.objects.filter(
            business=business,
            fecha_creacion__date=hoy,
            estado='completada'
        )
        total_ventas = ventas_hoy.aggregate(total=Sum('total'))['total'] or 0
        
        gastos_hoy = GastoCaja.objects.filter(
            business=business,
            fecha__date=hoy
        )
        total_gastos = gastos_hoy.aggregate(total=Sum('monto'))['total'] or 0
        
        efectivo_esperado = caja.monto_inicial + total_ventas - total_gastos
        diferencia = efectivo_real - efectivo_esperado
        
        # Cerrar caja
        caja.estado = 'cerrada'
        caja.monto_final = efectivo_real
        caja.diferencia = diferencia
        caja.usuario_cierre = request.user
        caja.fecha_cierre = timezone.now()
        caja.save()
        
        return JsonResponse({
            'success': True, 
            'message': 'Caja cerrada exitosamente',
            'diferencia': float(diferencia)
        })
        
    except Exception as e:
        logger.error(f"Error en caja_cerrar_api: {e}")
        return JsonResponse({'error': f'Error interno: {str(e)}'}, status=500)

@csrf_exempt
def caja_gastos_api(request):
    """API para manejar gastos de caja"""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Usuario no autenticado'}, status=401)
            
        if not hasattr(request.user, 'business'):
            return JsonResponse({'error': 'Usuario sin negocio asignado'}, status=400)
        
        business = request.user.business
        hoy = timezone.now().date()
        
        if request.method == 'GET':
            # Obtener gastos del día (con fallback si la tabla no existe)
            try:
                gastos = GastoCaja.objects.filter(
                    business=business,
                    fecha__date=hoy
                ).order_by('-fecha')
            except Exception as gastos_error:
                logger.error(f"Error accediendo a gastos: {gastos_error}")
                return JsonResponse([], safe=False)  # Devolver lista vacía
            
            gastos_data = []
            for gasto in gastos:
                tipo_display = {
                    'compra': 'Compra',
                    'gasto_operativo': 'Gasto Operativo',
                    'retiro': 'Retiro',
                    'otro': 'Otro'
                }.get(gasto.tipo, gasto.tipo)
                
                gastos_data.append({
                    'id': gasto.id,
                    'concepto': gasto.concepto,
                    'monto': float(gasto.monto),
                    'tipo': gasto.tipo,
                    'tipo_display': tipo_display,
                    'fecha': gasto.fecha.isoformat()
                })
            
            return JsonResponse(gastos_data, safe=False)
            
        elif request.method == 'POST':
            # Crear nuevo gasto
            import json
            data = json.loads(request.body)
            
            concepto = data.get('concepto', '').strip()
            monto = data.get('monto', 0)
            tipo = data.get('tipo', 'otro')
            
            if not concepto:
                return JsonResponse({'error': 'El concepto es requerido'}, status=400)
                
            if monto <= 0:
                return JsonResponse({'error': 'El monto debe ser mayor a 0'}, status=400)
            
            # Crear gasto
            gasto = GastoCaja.objects.create(
                business=business,
                concepto=concepto,
                monto=monto,
                tipo=tipo,
                usuario=request.user
            )
            
            return JsonResponse({'success': True, 'message': 'Gasto registrado exitosamente'})
        
    except Exception as e:
        logger.error(f"Error en caja_gastos_api: {e}")
        return JsonResponse({'error': f'Error interno: {str(e)}'}, status=500)

@csrf_exempt
def caja_test_api(request):
    """API de prueba simple para debugging caja"""
    try:
        return JsonResponse({
            'status': 'working',
            'user_authenticated': request.user.is_authenticated,
            'has_business': hasattr(request.user, 'business') if request.user.is_authenticated else False,
            'method': request.method
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt 
def setup_caja_db(request):
    """Vista para ejecutar setup de tablas de caja automáticamente"""
    try:
        from django.core.management import call_command
        from io import StringIO
        
        # Capturar output del comando
        out = StringIO()
        call_command('setup_caja_tables', stdout=out)
        output = out.getvalue()
        
        return JsonResponse({
            'success': True,
            'message': 'Tablas de caja configuradas',
            'output': output
        })
        
    except Exception as e:
        logger.error(f"Error en setup_caja_db: {e}")
        return JsonResponse({
            'success': False, 
            'error': str(e)
        }, status=500)

# ========================
# VIEWS INVENTARIO
# ========================

@login_required
def inventario_view(request):
    """Vista principal del inventario"""
    try:
        business = request.user.business
        productos = Producto.objects.filter(business=business).order_by('codigo')
        
        context = {
            'productos': productos,
            'total_productos': productos.count(),
            'business': business
        }
        return render(request, 'inventario/inventario.html', context)
    except Exception as e:
        logger.error(f"Error en inventario_view: {e}")
        return render(request, 'inventario/inventario.html', {
            'productos': [], 
            'error': str(e)
        })

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def agregar_producto_inventario(request):
    """API para agregar productos al inventario"""
    try:
        data = json.loads(request.body)
        
        required_fields = ['codigo', 'nombre', 'precio']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False, 
                    'error': f'Campo requerido: {field}'
                }, status=400)
        
        business = request.user.business
        
        # Verificar si el código ya existe
        if Producto.objects.filter(business=business, codigo=data['codigo']).exists():
            return JsonResponse({
                'success': False,
                'error': f'El código {data["codigo"]} ya existe'
            }, status=400)
        
        # Crear producto
        producto = Producto.objects.create(
            business=business,
            codigo=data['codigo'].upper(),
            nombre=data['nombre'],
            precio=Decimal(str(data['precio'])),
            stock=int(data.get('stock', 0)),
            stock_minimo=int(data.get('stock_minimo', 10))
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Producto agregado exitosamente',
            'producto': {
                'id': producto.id,
                'codigo': producto.codigo,
                'nombre': producto.nombre,
                'precio': float(producto.precio),
                'stock': producto.stock,
                'stock_minimo': producto.stock_minimo
            }
        })
        
    except Exception as e:
        logger.error(f"Error agregando producto: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Error interno: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@login_required
def actualizar_producto_inventario(request):
    """API para actualizar productos en inventario"""
    try:
        data = json.loads(request.body)
        codigo = data.get('codigo')
        
        if not codigo:
            return JsonResponse({
                'success': False,
                'error': 'Código de producto requerido'
            }, status=400)
        
        business = request.user.business
        
        try:
            producto = Producto.objects.get(business=business, codigo=codigo)
        except Producto.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Producto con código {codigo} no encontrado'
            }, status=404)
        
        # Actualizar campos
        stock_anterior = producto.stock  # Guardar stock anterior para el movimiento
        cantidad_agregada = 0

        if 'stock_agregar' in data:
            cantidad_agregada = int(data['stock_agregar'])
            producto.stock += cantidad_agregada

        if 'nuevo_precio' in data and data['nuevo_precio']:
            producto.precio = Decimal(str(data['nuevo_precio']))

        if 'stock_minimo' in data:
            producto.stock_minimo = int(data.get('stock_minimo', 10))

        producto.save()

        # Registrar movimiento de stock si se agregó cantidad
        if cantidad_agregada != 0:
            motivo_movimiento = f"Actualización de inventario - {producto.nombre}: inventario anterior: {stock_anterior}, stock agregado: {cantidad_agregada}, stock final: {producto.stock}"

            # Determinar tipo de movimiento
            tipo_movimiento = 'entrada' if cantidad_agregada > 0 else 'ajuste'

            MovimientoStock.objects.create(
                business=business,
                producto=producto,
                tipo_movimiento=tipo_movimiento,
                cantidad=cantidad_agregada,
                stock_anterior=stock_anterior,
                stock_nuevo=producto.stock,
                usuario=request.user,
                motivo=motivo_movimiento,
                ip_address=get_client_ip(request)
            )
        
        return JsonResponse({
            'success': True,
            'mensaje': 'Producto actualizado exitosamente',
            'producto': {
                'codigo': producto.codigo,
                'nombre': producto.nombre,
                'precio': float(producto.precio),
                'stock': producto.stock,
                'stock_minimo': producto.stock_minimo
            }
        })
        
    except Exception as e:
        logger.error(f"Error actualizando producto: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Error interno: {str(e)}'
        }, status=500)

@csrf_exempt
@login_required
def inventario_api(request):
    """API para obtener todos los productos del inventario"""
    try:
        business = request.user.business
        productos = Producto.objects.filter(business=business).order_by('codigo')
        
        productos_data = []
        for producto in productos:
            productos_data.append({
                'id': producto.id,
                'codigo': producto.codigo,
                'nombre': producto.nombre,
                'precio': float(producto.precio),
                'stock': producto.stock,
                'stock_minimo': producto.stock_minimo or 10
            })
        
        return JsonResponse(productos_data, safe=False)
        
    except Exception as e:
        logger.error(f"Error en inventario_api: {e}")
        return JsonResponse({'error': str(e)}, status=500)

# ========================
# STOCK ALERTS API
# ========================

@csrf_exempt
@login_required
def productos_poco_stock_api(request):
    """API para obtener productos con poco stock"""
    try:
        business = request.user.business
        
        # Obtener productos con stock bajo o crítico
        productos_bajo_stock = []
        productos = Producto.objects.filter(business=business, activo=True)
        
        for producto in productos:
            stock_minimo = producto.stock_minimo or 10
            
            # Criterios para stock bajo:
            # 1. Sin stock (crítico)
            # 2. Menos del stock mínimo configurado
            if producto.stock <= 0 or producto.stock < stock_minimo:
                productos_bajo_stock.append({
                    'codigo': producto.codigo,
                    'nombre': producto.nombre,
                    'stock': producto.stock,
                    'stock_minimo': stock_minimo,
                    'precio': float(producto.precio),
                    'categoria': getattr(producto, 'categoria', 'Sin categoría')
                })
        
        return JsonResponse({
            'productos_bajo_stock': productos_bajo_stock,
            'total_productos_bajo_stock': len(productos_bajo_stock),
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error en productos_poco_stock_api: {e}")
        return JsonResponse({'error': str(e)}, status=500)

# ========================
# CONTROL DE CAJA
# ========================

@login_required
def control_caja(request):
    """Vista para control de caja"""
    try:
        business = request.user.business
        
        # Buscar caja abierta del día (simplificado)
        context = {
            'business': business,
            'mensaje': 'Control de caja funcionando'
        }
        return render(request, 'pos/caja.html', context)
        
    except Exception as e:
        logger.error(f"Error en control_caja: {e}")
        return render(request, 'pos/caja.html', {'error': str(e)})

# ========================
# PRODUCT MANAGEMENT API - EDIT AND DELETE
# ========================

@csrf_exempt
@login_required
def obtener_producto_por_id(request, producto_id):
    """API para obtener un producto específico por ID para edición"""
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        business = request.user.business
        producto = get_object_or_404(Producto, id=producto_id, business=business)
        
        return JsonResponse({
            'id': producto.id,
            'codigo': producto.codigo,
            'nombre': producto.nombre,
            'precio': float(producto.precio),
            'stock': producto.stock,
            'stock_minimo': producto.stock_minimo or 10,
            'activo': producto.activo
        })
        
    except Exception as e:
        logger.error(f"Error en obtener_producto_por_id: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@login_required
@require_http_methods(["DELETE"])
def eliminar_producto_inventario(request, producto_id):
    """API para eliminar un producto del inventario"""
    try:
        business = request.user.business
        producto = get_object_or_404(Producto, id=producto_id, business=business)
        
        # Verificar si el producto tiene ventas asociadas
        if VentaDetalle.objects.filter(producto=producto).exists():
            # En lugar de eliminar físicamente, marcamos como inactivo
            producto.activo = False
            producto.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Producto "{producto.nombre}" desactivado exitosamente (tenía ventas asociadas)',
                'action': 'deactivated'
            })
        else:
            # Si no tiene ventas, se puede eliminar físicamente
            nombre_producto = producto.nombre
            producto.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Producto "{nombre_producto}" eliminado exitosamente',
                'action': 'deleted'
            })
        
    except Producto.DoesNotExist:
        return JsonResponse({'error': 'Producto no encontrado'}, status=404)
    except Exception as e:
        logger.error(f"Error en eliminar_producto_inventario: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@login_required
def obtener_stock_producto(request, codigo):
    """
    Obtiene el stock actual de un producto específico por código
    Para verificar alertas después de ventas
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido'}, status=405)
    
    try:
        business = request.user.business
        producto = get_object_or_404(Producto, codigo=codigo, business=business)
        
        return JsonResponse({
            'codigo': producto.codigo,
            'nombre': producto.nombre,
            'stock_actual': producto.stock,
            'stock_minimo': producto.stock_minimo or 10,
            'activo': producto.activo
        })
        
    except Exception as e:
        logger.error(f"Error en obtener_stock_producto: {e}")
        return JsonResponse({'error': str(e)}, status=500)

# ========================
# API MOVIMIENTOS DE STOCK
# ========================

@csrf_exempt
@login_required
@require_http_methods(["POST"])
def registrar_movimiento_stock(request):
    """API para registrar movimientos de stock manuales (entradas, ajustes, etc.)"""
    try:
        data = json.loads(request.body)

        codigo_producto = data.get('codigo_producto')
        tipo_movimiento = data.get('tipo_movimiento')
        cantidad = int(data.get('cantidad', 0))
        motivo = data.get('motivo', '')

        if not codigo_producto or not tipo_movimiento:
            return JsonResponse({
                'success': False,
                'error': 'Código de producto y tipo de movimiento son requeridos'
            }, status=400)

        if cantidad == 0:
            return JsonResponse({
                'success': False,
                'error': 'La cantidad debe ser diferente de cero'
            }, status=400)

        business = request.user.business

        try:
            producto = Producto.objects.get(business=business, codigo=codigo_producto)
        except Producto.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Producto con código {codigo_producto} no encontrado'
            }, status=404)

        # Obtener stock actual
        stock_anterior = producto.stock

        # Calcular nuevo stock basado en el tipo de movimiento
        if tipo_movimiento in ['entrada', 'compra']:
            stock_nuevo = stock_anterior + abs(cantidad)
            cantidad_movimiento = abs(cantidad)
        elif tipo_movimiento in ['salida', 'merma']:
            if stock_anterior < abs(cantidad):
                return JsonResponse({
                    'success': False,
                    'error': f'Stock insuficiente. Stock actual: {stock_anterior}'
                }, status=400)
            stock_nuevo = stock_anterior - abs(cantidad)
            cantidad_movimiento = -abs(cantidad)
        elif tipo_movimiento == 'ajuste':
            # Para ajuste, la cantidad puede ser positiva o negativa
            stock_nuevo = max(0, stock_anterior + cantidad)
            cantidad_movimiento = cantidad
        else:
            return JsonResponse({
                'success': False,
                'error': f'Tipo de movimiento "{tipo_movimiento}" no válido'
            }, status=400)

        # Crear registro de movimiento
        movimiento = MovimientoStock.objects.create(
            business=business,
            producto=producto,
            tipo_movimiento=tipo_movimiento,
            cantidad=cantidad_movimiento,
            stock_anterior=stock_anterior,
            stock_nuevo=stock_nuevo,
            usuario=request.user,
            motivo=motivo or f'{tipo_movimiento.title()} manual - {abs(cantidad)} unidades',
            ip_address=get_client_ip(request)
        )

        # Actualizar stock del producto
        producto.stock = stock_nuevo
        producto.save()

        return JsonResponse({
            'success': True,
            'message': f'Movimiento registrado exitosamente',
            'movimiento_id': movimiento.id,
            'stock_anterior': stock_anterior,
            'stock_nuevo': stock_nuevo,
            'producto': {
                'codigo': producto.codigo,
                'nombre': producto.nombre,
                'stock': producto.stock
            }
        })

    except Exception as e:
        logger.error(f"Error registrando movimiento de stock: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Error interno: {str(e)}'
        }, status=500)


@csrf_exempt
@login_required
def obtener_movimientos_stock(request):
    """API para obtener historial de movimientos de stock"""
    try:
        business = request.user.business

        # Parámetros de filtro
        codigo_producto = request.GET.get('codigo_producto')
        tipo_movimiento = request.GET.get('tipo_movimiento')
        fecha_inicio = request.GET.get('fecha_inicio')
        fecha_fin = request.GET.get('fecha_fin')
        limite = int(request.GET.get('limite', 50))

        # Base queryset
        movimientos = MovimientoStock.objects.filter(business=business)

        # Aplicar filtros
        if codigo_producto:
            movimientos = movimientos.filter(producto__codigo=codigo_producto)

        if tipo_movimiento:
            movimientos = movimientos.filter(tipo_movimiento=tipo_movimiento)

        if fecha_inicio:
            from datetime import datetime
            fecha_inicio_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            movimientos = movimientos.filter(fecha_movimiento__gte=fecha_inicio_dt)

        if fecha_fin:
            from datetime import datetime
            fecha_fin_dt = datetime.strptime(fecha_fin, '%Y-%m-%d')
            movimientos = movimientos.filter(fecha_movimiento__lte=fecha_fin_dt)

        # Ordenar y limitar
        movimientos = movimientos.order_by('-fecha_movimiento')[:limite]

        # Construir respuesta
        movimientos_data = []
        for mov in movimientos:
            movimientos_data.append({
                'id': mov.id,
                'fecha': mov.fecha_movimiento.isoformat(),
                'producto': {
                    'codigo': mov.producto.codigo,
                    'nombre': mov.producto.nombre
                },
                'tipo_movimiento': mov.tipo_movimiento,
                'tipo_movimiento_display': mov.get_tipo_movimiento_display(),
                'cantidad': mov.cantidad,
                'stock_anterior': mov.stock_anterior,
                'stock_nuevo': mov.stock_nuevo,
                'motivo': mov.motivo,
                'usuario': mov.usuario.username,
                'venta_folio': mov.venta.folio if mov.venta else None
            })

        return JsonResponse({
            'movimientos': movimientos_data,
            'total_encontrados': len(movimientos_data)
        })

    except Exception as e:
        logger.error(f"Error obteniendo movimientos de stock: {e}")
        return JsonResponse({
            'error': f'Error interno: {str(e)}'
        }, status=500)


def crear_vista_agrupada_jerarquica(business, ventas, movimientos):
    """Crear vista jerárquica: años → meses → semanas → días"""
    from datetime import timedelta, datetime
    from django.utils import timezone
    from django.db.models import Sum
    from collections import defaultdict
    import calendar

    # Obtener fecha actual en timezone de México
    from zoneinfo import ZoneInfo
    mexico_tz = ZoneInfo('America/Mexico_City')
    ahora_mexico = timezone.now().astimezone(mexico_tz)
    hoy = ahora_mexico.date()

    # Calcular total del día actual usando timezone local
    ventas_hoy = Venta.objects.filter(
        business=business,
        estado='completada',
        fecha_creacion__date=hoy
    )
    total_del_dia = ventas_hoy.aggregate(total=Sum('total'))['total'] or 0

    # Agrupar ventas por jerarquía
    jerarquia = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(list))))

    for venta in ventas:
        fecha = venta.fecha_creacion.date()
        anio = fecha.year
        mes = fecha.month

        # Calcular semana del mes
        primer_dia_mes = fecha.replace(day=1)
        dias_desde_inicio = (fecha - primer_dia_mes).days
        semana_del_mes = (dias_desde_inicio // 7) + 1

        jerarquia[anio][mes][semana_del_mes][fecha].append({
            'tipo': 'venta',
            'venta': venta,
            'fecha': fecha
        })

    # Agrupar movimientos de stock
    for movimiento in movimientos:
        fecha = movimiento.fecha_movimiento.date()
        anio = fecha.year
        mes = fecha.month

        # Calcular semana del mes
        primer_dia_mes = fecha.replace(day=1)
        dias_desde_inicio = (fecha - primer_dia_mes).days
        semana_del_mes = (dias_desde_inicio // 7) + 1

        jerarquia[anio][mes][semana_del_mes][fecha].append({
            'tipo': 'movimiento_stock',
            'movimiento': movimiento,
            'fecha': fecha
        })

    # Construir estructura de respuesta
    grupos_anios = []

    for anio in sorted(jerarquia.keys(), reverse=True):
        # Calcular total del año
        total_anio = Venta.objects.filter(
            business=business,
            estado='completada',
            fecha_creacion__year=anio
        ).aggregate(total=Sum('total'))['total'] or 0

        grupos_meses = []
        for mes in sorted(jerarquia[anio].keys(), reverse=True):
            # Calcular total del mes
            total_mes = Venta.objects.filter(
                business=business,
                estado='completada',
                fecha_creacion__year=anio,
                fecha_creacion__month=mes
            ).aggregate(total=Sum('total'))['total'] or 0

            grupos_semanas = []
            for semana in sorted(jerarquia[anio][mes].keys(), reverse=True):
                grupos_dias = []
                total_semana = 0

                for fecha_dia in sorted(jerarquia[anio][mes][semana].keys(), reverse=True):
                    actividades_dia = jerarquia[anio][mes][semana][fecha_dia]

                    # Calcular total del día
                    total_dia = Venta.objects.filter(
                        business=business,
                        estado='completada',
                        fecha_creacion__date=fecha_dia
                    ).aggregate(total=Sum('total'))['total'] or 0

                    total_semana += total_dia

                    # Preparar actividades del día
                    actividades_formateadas = []
                    for actividad in actividades_dia:
                        if actividad['tipo'] == 'venta':
                            venta = actividad['venta']
                            usuario_nombre = f"{venta.usuario.first_name} {venta.usuario.last_name}".strip() or venta.usuario.username

                            actividades_formateadas.append({
                                'tipo': 'venta',
                                'id': venta.id,
                                'fecha': venta.fecha_creacion.isoformat(),
                                'titulo': f"💰 Venta #{venta.folio}",
                                'usuario': usuario_nombre,
                                'total': float(venta.total),
                                'metodo_pago': venta.get_metodo_pago_display(),
                                'productos': [
                                    {
                                        'nombre': detalle.producto.nombre,
                                        'cantidad': detalle.cantidad,
                                        'precio_unitario': float(detalle.precio_unitario),
                                        'subtotal': float(detalle.subtotal)
                                    }
                                    for detalle in venta.detalles.all()
                                ],
                                'movimientos_stock': [
                                    {
                                        'producto': mov.producto.nombre,
                                        'stock_anterior': mov.stock_anterior,
                                        'cantidad': mov.cantidad,
                                        'stock_nuevo': mov.stock_nuevo
                                    }
                                    for mov in venta.movimientos_stock.all()
                                ]
                            })
                        else:
                            movimiento = actividad['movimiento']
                            usuario_nombre = f"{movimiento.usuario.first_name} {movimiento.usuario.last_name}".strip() or movimiento.usuario.username

                            iconos_tipo = {
                                'entrada': '📦⬆️',
                                'compra': '🛒',
                                'ajuste': '⚖️',
                                'salida': '📦⬇️',
                                'merma': '💸',
                                'devolucion': '↩️'
                            }

                            actividades_formateadas.append({
                                'tipo': 'movimiento_stock',
                                'id': movimiento.id,
                                'fecha': movimiento.fecha_movimiento.isoformat(),
                                'titulo': f"{iconos_tipo.get(movimiento.tipo_movimiento, '📦')} {movimiento.get_tipo_movimiento_display()}",
                                'usuario': usuario_nombre,
                                'motivo': movimiento.motivo,
                                'producto': {
                                    'nombre': movimiento.producto.nombre,
                                    'codigo': movimiento.producto.codigo,
                                    'stock_anterior': movimiento.stock_anterior,
                                    'cantidad_movida': movimiento.cantidad,
                                    'stock_nuevo': movimiento.stock_nuevo
                                }
                            })

                    grupos_dias.append({
                        'tipo': 'dia',
                        'fecha': fecha_dia.isoformat(),
                        'titulo': fecha_dia.strftime('%d/%m/%Y'),
                        'es_hoy': fecha_dia == hoy,
                        'total': float(total_dia),
                        'actividades': actividades_formateadas
                    })

                grupos_semanas.append({
                    'tipo': 'semana',
                    'titulo': f"Semana {semana}",
                    'total': float(total_semana),
                    'dias': grupos_dias
                })

            meses_es = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                       'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
            nombre_mes = meses_es[mes]
            grupos_meses.append({
                'tipo': 'mes',
                'titulo': f"{nombre_mes} {anio}",
                'total': float(total_mes),
                'semanas': grupos_semanas
            })

        grupos_anios.append({
            'tipo': 'anio',
            'titulo': str(anio),
            'total': float(total_anio),
            'meses': grupos_meses
        })

    return JsonResponse({
        'es_vista_jerarquica': True,
        'grupos_jerarquicos': grupos_anios,
        'total_del_dia': float(total_del_dia)
    })


@csrf_exempt
@login_required
def registro_completo_api(request):
    """API unificada para mostrar ventas y movimientos de stock en una sola vista cronológica"""
    try:
        business = request.user.business

        # Parámetros de filtro
        fecha_inicio = request.GET.get('fecha_inicio')
        fecha_fin = request.GET.get('fecha_fin')
        limite = int(request.GET.get('limite', 50))
        vista_agrupada = request.GET.get('agrupada', 'true').lower() == 'true'

        # Nuevos filtros de fecha compatible con frontend existente
        dia = request.GET.get('dia')
        mes = request.GET.get('mes')
        anio = request.GET.get('anio')
        producto_filtro = request.GET.get('producto')

        from datetime import timedelta
        from django.utils import timezone
        from django.db.models import Q

        hoy = timezone.now().date()

        # Procesar filtros de fecha del frontend existente
        if dia:
            fecha_inicio = dia
            fecha_fin = dia
        elif mes:
            año, mes_num = mes.split('-')
            from datetime import datetime
            primer_dia = datetime(int(año), int(mes_num), 1).date()
            if int(mes_num) == 12:
                ultimo_dia = datetime(int(año) + 1, 1, 1).date() - timedelta(days=1)
            else:
                ultimo_dia = datetime(int(año), int(mes_num) + 1, 1).date() - timedelta(days=1)
            fecha_inicio = primer_dia.isoformat()
            fecha_fin = ultimo_dia.isoformat()
        elif anio:
            fecha_inicio = f"{anio}-01-01"
            fecha_fin = f"{anio}-12-31"
        elif not fecha_inicio and not fecha_fin:
            # Si no hay filtros, mostrar últimos 7 días
            fecha_inicio = (hoy - timedelta(days=7)).isoformat()
            fecha_fin = hoy.isoformat()

        # Obtener ventas
        ventas_query = Venta.objects.filter(
            business=business,
            estado='completada'
        ).select_related('usuario').prefetch_related('detalles__producto', 'movimientos_stock')

        # Obtener movimientos de stock que NO sean de ventas (entradas manuales, ajustes, etc.)
        movimientos_query = MovimientoStock.objects.filter(
            business=business
        ).exclude(
            tipo_movimiento='venta'  # Excluir movimientos de venta (ya están en ventas)
        ).select_related('usuario', 'producto')

        # Aplicar filtros de fecha
        if fecha_inicio:
            fecha_inicio_dt = timezone.datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
            ventas_query = ventas_query.filter(fecha_creacion__date__gte=fecha_inicio_dt)
            movimientos_query = movimientos_query.filter(fecha_movimiento__date__gte=fecha_inicio_dt)

        if fecha_fin:
            fecha_fin_dt = timezone.datetime.strptime(fecha_fin, '%Y-%m-%d').date()
            ventas_query = ventas_query.filter(fecha_creacion__date__lte=fecha_fin_dt)
            movimientos_query = movimientos_query.filter(fecha_movimiento__date__lte=fecha_fin_dt)

        # Aplicar filtro por producto
        if producto_filtro:
            # Filtrar ventas que contengan este producto
            ventas_query = ventas_query.filter(
                Q(detalles__producto__codigo__icontains=producto_filtro) |
                Q(detalles__producto__nombre__icontains=producto_filtro)
            ).distinct()

            # Filtrar movimientos de stock de este producto
            movimientos_query = movimientos_query.filter(
                Q(producto__codigo__icontains=producto_filtro) |
                Q(producto__nombre__icontains=producto_filtro)
            )

        # Obtener datos
        ventas = ventas_query.order_by('-fecha_creacion')
        movimientos = movimientos_query.order_by('-fecha_movimiento')

        # Si no hay filtros específicos, crear vista agrupada jerárquica
        if vista_agrupada and not dia and not mes and not anio and not producto_filtro:
            return crear_vista_agrupada_jerarquica(business, ventas, movimientos)

        # Crear lista unificada de actividades
        actividades = []

        # Agregar ventas
        for venta in ventas:
            usuario_nombre = f"{venta.usuario.first_name} {venta.usuario.last_name}".strip() or venta.usuario.username

            actividades.append({
                'tipo': 'venta',
                'id': venta.id,
                'fecha': venta.fecha_creacion.isoformat(),
                'titulo': f"💰 Venta #{venta.folio}",
                'usuario': usuario_nombre,
                'total': float(venta.total),
                'metodo_pago': venta.get_metodo_pago_display(),
                'productos': [
                    {
                        'nombre': detalle.producto.nombre,
                        'cantidad': detalle.cantidad,
                        'precio_unitario': float(detalle.precio_unitario),
                        'subtotal': float(detalle.subtotal)
                    }
                    for detalle in venta.detalles.all()
                ],
                'movimientos_stock': [
                    {
                        'producto': mov.producto.nombre,
                        'stock_anterior': mov.stock_anterior,
                        'cantidad': mov.cantidad,
                        'stock_nuevo': mov.stock_nuevo
                    }
                    for mov in venta.movimientos_stock.all()
                ]
            })

        # Agregar movimientos de stock (entradas, ajustes, etc.)
        for movimiento in movimientos:
            usuario_nombre = f"{movimiento.usuario.first_name} {movimiento.usuario.last_name}".strip() or movimiento.usuario.username

            # Determinar icono y color según tipo
            iconos_tipo = {
                'entrada': '📦⬆️',
                'compra': '🛒',
                'ajuste': '⚖️',
                'salida': '📦⬇️',
                'merma': '💸',
                'devolucion': '↩️'
            }

            actividades.append({
                'tipo': 'movimiento_stock',
                'id': movimiento.id,
                'fecha': movimiento.fecha_movimiento.isoformat(),
                'titulo': f"{iconos_tipo.get(movimiento.tipo_movimiento, '📦')} {movimiento.get_tipo_movimiento_display()}",
                'usuario': usuario_nombre,
                'motivo': movimiento.motivo,
                'producto': {
                    'nombre': movimiento.producto.nombre,
                    'codigo': movimiento.producto.codigo,
                    'stock_anterior': movimiento.stock_anterior,
                    'cantidad_movida': movimiento.cantidad,
                    'stock_nuevo': movimiento.stock_nuevo
                }
            })

        # Ordenar todo por fecha (más reciente primero)
        actividades.sort(key=lambda x: x['fecha'], reverse=True)

        # Calcular total del día actual usando timezone de México
        from django.db.models import Sum
        from zoneinfo import ZoneInfo
        mexico_tz = ZoneInfo('America/Mexico_City')
        ahora_mexico = timezone.now().astimezone(mexico_tz)
        hoy = ahora_mexico.date()

        ventas_hoy = Venta.objects.filter(
            business=business,
            estado='completada',
            fecha_creacion__date=hoy
        )
        total_del_dia = ventas_hoy.aggregate(total=Sum('total'))['total'] or 0

        # Limitar resultados
        if limite > 0:
            actividades = actividades[:limite]

        return JsonResponse({
            'actividades': actividades,
            'total_actividades': len(actividades),
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'total_del_dia': float(total_del_dia)
        })

    except Exception as e:
        logger.error(f"Error en registro_completo_api: {e}")
        return JsonResponse({
            'error': f'Error interno: {str(e)}',
            'actividades': []
        }, status=500)


@csrf_exempt
@login_required
def movimientos_stock_api(request):
    """API para obtener historial de movimientos de stock para el frontend"""
    try:
        business = request.user.business

        # Parámetros de filtro
        limite = int(request.GET.get('limite', 50))
        tipo_movimiento = request.GET.get('tipo_movimiento')
        producto_id = request.GET.get('producto_id')
        fecha_desde = request.GET.get('fecha_desde')
        fecha_hasta = request.GET.get('fecha_hasta')

        # Base queryset
        movimientos = MovimientoStock.objects.filter(business=business).select_related(
            'producto', 'usuario', 'venta'
        )

        # Aplicar filtros
        if tipo_movimiento:
            movimientos = movimientos.filter(tipo_movimiento=tipo_movimiento)

        if producto_id:
            movimientos = movimientos.filter(producto__id=producto_id)

        if fecha_desde:
            from datetime import datetime
            fecha_desde_dt = datetime.strptime(fecha_desde, '%Y-%m-%d')
            movimientos = movimientos.filter(fecha_movimiento__gte=fecha_desde_dt)

        if fecha_hasta:
            from datetime import datetime
            fecha_hasta_dt = datetime.strptime(fecha_hasta, '%Y-%m-%d')
            movimientos = movimientos.filter(fecha_movimiento__lte=fecha_hasta_dt)

        # Ordenar y limitar
        movimientos = movimientos.order_by('-fecha_movimiento')[:limite]

        # Construir respuesta
        movimientos_data = []
        for mov in movimientos:
            usuario_nombre = f"{mov.usuario.first_name} {mov.usuario.last_name}".strip() or mov.usuario.username

            movimiento_info = {
                'id': mov.id,
                'fecha': mov.fecha_movimiento.isoformat(),
                'tipo_movimiento': mov.tipo_movimiento,
                'tipo_movimiento_display': mov.get_tipo_movimiento_display(),
                'cantidad': mov.cantidad,
                'stock_anterior': mov.stock_anterior,
                'stock_nuevo': mov.stock_nuevo,
                'motivo': mov.motivo,
                'usuario': {
                    'username': mov.usuario.username,
                    'nombre_completo': usuario_nombre
                },
                'producto': {
                    'id': mov.producto.id,
                    'codigo': mov.producto.codigo,
                    'nombre': mov.producto.nombre,
                    'stock_actual': mov.producto.stock
                }
            }

            # Agregar información de venta si existe
            if mov.venta:
                movimiento_info['venta'] = {
                    'id': mov.venta.id,
                    'folio': mov.venta.folio,
                    'total': float(mov.venta.total),
                    'fecha': mov.venta.fecha_creacion.isoformat()
                }

            movimientos_data.append(movimiento_info)

        # Obtener estadísticas
        total_movimientos = MovimientoStock.objects.filter(business=business).count()
        movimientos_hoy = MovimientoStock.objects.filter(
            business=business,
            fecha_movimiento__date=timezone.now().date()
        ).count()

        return JsonResponse({
            'movimientos': movimientos_data,
            'total_encontrados': len(movimientos_data),
            'total_movimientos': total_movimientos,
            'movimientos_hoy': movimientos_hoy,
            'tipos_disponibles': [
                {'value': 'venta', 'label': 'Ventas'},
                {'value': 'entrada', 'label': 'Entradas'},
                {'value': 'salida', 'label': 'Salidas'},
                {'value': 'ajuste', 'label': 'Ajustes'},
                {'value': 'compra', 'label': 'Compras'},
                {'value': 'devolucion', 'label': 'Devoluciones'},
                {'value': 'merma', 'label': 'Mermas'}
            ]
        })

    except Exception as e:
        logger.error(f"Error en movimientos_stock_api: {e}")
        return JsonResponse({
            'error': f'Error interno: {str(e)}',
            'movimientos': []
        }, status=500)