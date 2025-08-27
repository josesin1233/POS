from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.conf import settings
from pos.models import Producto, Venta, VentaDetalle, Caja, GastoCaja, Sucursal
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
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Autenticación requerida'}, status=401)
        
        data = json.loads(request.body)
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
        
        # Crear detalles y actualizar stock
        for item in productos_venta:
            VentaDetalle.objects.create(
                venta=venta,
                producto=item['producto'],
                cantidad=item['cantidad'],
                precio_unitario=item['precio_unitario'],
                subtotal=item['subtotal']
            )
            
            # Actualizar stock
            item['producto'].stock -= item['cantidad']
            item['producto'].save()
        
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
        
        hoy = timezone.now().date()
        
        # Obtener parámetros de filtro
        dia = request.GET.get('dia')
        mes = request.GET.get('mes')
        anio = request.GET.get('anio')
        
        # Calcular total del día actual siempre
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
                    'detalles': [
                        {
                            'producto': {'nombre': detalle.producto.nombre},
                            'cantidad': detalle.cantidad,
                            'precio_unitario': float(detalle.precio_unitario)
                        }
                        for detalle in venta.detalles.all()
                    ]
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
                'productos': productos_venta
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
        
        business = request.user.business
        hoy = timezone.now().date()
        
        # Buscar caja del día
        try:
            caja = Caja.objects.get(business=business, fecha_apertura__date=hoy)
            estado = 'abierta' if caja.estado == 'abierta' else 'cerrada'
            monto_actual = float(caja.monto_inicial)  # Usar monto_inicial por ahora
        except Caja.DoesNotExist:
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
        
        # Calcular gastos del día
        gastos_hoy = GastoCaja.objects.filter(
            business=business,
            fecha__date=hoy
        )
        total_gastos = gastos_hoy.aggregate(total=Sum('monto'))['total'] or 0
        
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
        
        # Verificar si ya existe una caja para hoy
        caja_existente = Caja.objects.filter(business=business, fecha_apertura__date=hoy).first()
        if caja_existente:
            return JsonResponse({'error': 'Ya existe una caja para el día de hoy'}, status=400)
        
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
            # Obtener gastos del día
            gastos = GastoCaja.objects.filter(
                business=business,
                fecha__date=hoy
            ).order_by('-fecha')
            
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
        if 'stock_agregar' in data:
            producto.stock += int(data['stock_agregar'])
        
        if 'nuevo_precio' in data and data['nuevo_precio']:
            producto.precio = Decimal(str(data['nuevo_precio']))
        
        if 'stock_minimo' in data:
            producto.stock_minimo = int(data.get('stock_minimo', 10))
        
        producto.save()
        
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
            # 3. Menos de 5 unidades (advertencia)
            if producto.stock <= 0 or producto.stock < stock_minimo or producto.stock <= 5:
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