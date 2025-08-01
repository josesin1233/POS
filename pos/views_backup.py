from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators	.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from decimal import Decimal
import json
import logging

from .models import Producto, Venta, VentaDetalle, ResumenDiario
from .utils import redondear_personalizado

logger = logging.getLogger(__name__)



def index(request):
    """Página principal del POS"""
    context = {
        'business': request.user.business,
        'user': request.user,
    }
    return render(request, 'pos/index.html', context)


@method_decorator(csrf_exempt, name='dispatch')
class ProductoAPIView(View):
    """API para buscar productos por código o nombre"""
    def post(self, request):
        try:
            data = json.loads(request.body)
            codigo = data.get('codigo', '').strip()
            nombre = data.get('nombre', '').strip()
            
            business_id = 1
           producto = Producto.objects.filter(
    business_id=business_id,
    nombre__iexact=nombre
).first()
            
            if codigo:
    producto = Producto.objects.filter(
        business_id=business_id,
        codigo=codigo
    ).first()
            elif nombre:
                producto = Producto.objects.filter(
                    business=business,
                    nombre__iexact=nombre
                ).first()
            
            if not producto:
                return JsonResponse({'error': 'Producto no encontrado'}, status=404)
            
            return JsonResponse({
                'codigo': producto.codigo,
                'nombre': producto.nombre,
                'precio': float(producto.precio),
                'stock': producto.stock,
                'stock_minimo': producto.stock_minimo
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)
        except Exception as e:
            logger.error(f"Error en ProductoAPIView: {e}")
            return JsonResponse({'error': 'Error interno del servidor'}, status=500)


@method_decorator(login_required, name='dispatch')
class AgregarProductoView(View):
    """API para agregar productos al carrito con redondeo"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            codigo = data.get('codigo', '').strip()
            nombre = data.get('nombre', '').strip()
            cantidad = data.get('cantidad', 1)
            
            if not isinstance(cantidad, int) or cantidad <= 0:
                return JsonResponse({'error': 'Cantidad inválida'}, status=400)
            
            business = request.user.business
            
            # Buscar producto
            if codigo:
                producto = Producto.objects.filter(business=business, codigo=codigo).first()
            elif nombre:
                producto = Producto.objects.filter(business=business, nombre__iexact=nombre).first()
            else:
                return JsonResponse({'error': 'Código o nombre requerido'}, status=400)
            
            if not producto:
                return JsonResponse({'error': 'Producto no encontrado'}, status=404)
            
            if producto.stock < cantidad:
                return JsonResponse({'error': 'Stock insuficiente'}, status=400)
            
            # Calcular total con redondeo personalizado
            total = producto.precio * cantidad
            precio_total_redondeado = redondear_personalizado(total)
            
            return JsonResponse({
                'codigo': producto.codigo,
                'nombre': producto.nombre,
                'precio_unitario': float(producto.precio),
                'cantidad': cantidad,
                'precio_total': float(precio_total_redondeado)
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)
        except Exception as e:
            logger.error(f"Error en AgregarProductoView: {e}")
            return JsonResponse({'error': 'Error interno del servidor'}, status=500)


@method_decorator(login_required, name='dispatch')
class RegistrarVentaView(View):
    """API para registrar una venta completa"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            productos_vendidos = data.get('productos', [])
            monto_pagado = data.get('monto_pagado', 0)
            
            if not productos_vendidos or not isinstance(productos_vendidos, list):
                return JsonResponse({'error': 'Lista de productos inválida'}, status=400)
            
            business = request.user.business
            
            with transaction.atomic():
                # Validar productos y calcular total
                venta_productos = []
                total_venta = Decimal('0.00')
                
                for item in productos_vendidos:
                    codigo = item.get('codigo')
                    cantidad = int(item.get('cantidad', 0))
                    
                    if not codigo or cantidad <= 0:
                        return JsonResponse({'error': 'Código o cantidad inválida'}, status=400)
                    
                    producto = Producto.objects.select_for_update().filter(
                        business=business,
                        codigo=codigo
                    ).first()
                    
                    if not producto:
                        return JsonResponse({'error': f'Producto {codigo} no encontrado'}, status=404)
                    
                    if producto.stock < cantidad:
                        return JsonResponse({'error': f'Stock insuficiente para {producto.nombre}'}, status=400)
                    
                    # Preparar datos de la venta
                    total_producto = producto.precio * cantidad
                    total_producto_redondeado = redondear_personalizado(total_producto)
                    
                    venta_productos.append({
                        'producto': producto,
                        'cantidad': cantidad,
                        'precio_unitario': producto.precio,
                        'total': total_producto_redondeado
                    })
                    
                    total_venta += total_producto_redondeado
                
                # Crear la venta
                venta = Venta.objects.create(
                    business=business,
                    vendedor=request.user,
                    total_venta=total_venta,
                    monto_pagado=Decimal(str(monto_pagado)) if monto_pagado else total_venta
                )
                
                # Calcular cambio
                cambio = venta.calcular_cambio(venta.monto_pagado)
                
                # Crear detalles de venta y actualizar stock
                for item in venta_productos:
                    VentaDetalle.objects.create(
                        venta=venta,
                        producto=item['producto'],
                        codigo_producto=item['producto'].codigo,
                        nombre_producto=item['producto'].nombre,
                        precio_unitario=item['precio_unitario'],
                        cantidad_vendida=item['cantidad'],
                        total=item['total']
                    )
                    
                    # Reducir stock
                    item['producto'].reducir_stock(item['cantidad'])
                
                # Actualizar resumen diario
                resumen = ResumenDiario.obtener_o_crear_hoy(business)
                resumen.actualizar_totales()
                
                return JsonResponse({
                    'mensaje': 'Venta registrada exitosamente',
                    'venta_id': venta.id,
                    'total_venta': float(total_venta),
                    'cambio': float(cambio),
                    'fecha': venta.fecha.isoformat()
                })
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)
        except ValueError as e:
            return JsonResponse({'error': f'Error en los datos: {e}'}, status=400)
        except Exception as e:
            logger.error(f"Error en RegistrarVentaView: {e}")
            return JsonResponse({'error': 'Error interno del servidor'}, status=500)


@method_decorator(login_required, name='dispatch')
class TotalVentasHoyView(View):
    """API para obtener el total de ventas del día"""
    
    def get(self, request):
        try:
            business = request.user.business
            resumen = ResumenDiario.obtener_o_crear_hoy(business)
            
            return JsonResponse({
                'total_hoy': float(resumen.total_ventas),
                'numero_ventas': resumen.numero_ventas,
                'productos_vendidos': resumen.productos_vendidos
            })
            
        except Exception as e:
            logger.error(f"Error en TotalVentasHoyView: {e}")
            return JsonResponse({'error': 'Error interno del servidor'}, status=500)


@method_decorator(login_required, name='dispatch')
class CerrarDiaView(View):
    """API para cerrar el día y enviar reporte"""
    
    def post(self, request):
        try:
            business = request.user.business
            hoy = timezone.now().date()
            
            # Obtener resumen del día
            resumen = ResumenDiario.objects.filter(
                business=business,
                fecha=hoy
            ).first()
            
            if not resumen or resumen.total_ventas == 0:
                return JsonResponse({'error': 'No hay ventas registradas para hoy'}, status=404)
            
            # Cerrar el día
            if resumen.cerrar_dia(request.user):
                # Enviar reporte por correo si está configurado
                if business.settings.send_daily_reports and business.settings.report_email:
                    self._enviar_reporte_correo(business, resumen)
                
                return JsonResponse({
                    'mensaje': 'Día cerrado exitosamente',
                    'total_dia': float(resumen.total_ventas),
                    'numero_ventas': resumen.numero_ventas
                })
            else:
                return JsonResponse({'error': 'El día ya fue cerrado'}, status=400)
                
        except Exception as e:
            logger.error(f"Error en CerrarDiaView: {e}")
            return JsonResponse({'error': 'Error interno del servidor'}, status=500)
    
    def _enviar_reporte_correo(self, business, resumen):
        """Envía el reporte diario por correo"""
        try:
            # Obtener productos con poco stock
            productos_bajo_stock = Producto.objects.filter(
                business=business,
                stock__lte=models.F('stock_minimo'),
                stock_minimo__gt=0
            )
            
            # Construir mensaje
            mensaje = f"""
🧾 Reporte diario - {business.name}
Fecha: {resumen.fecha.strftime('%d/%m/%Y')}

📊 Resumen de ventas:
• Total de ventas: ${resumen.total_ventas:,.2f}
• Número de ventas: {resumen.numero_ventas}
• Productos vendidos: {resumen.productos_vendidos}

"""
            
            if productos_bajo_stock.exists():
                mensaje += "⚠️ Productos con stock bajo:\n"
                for producto in productos_bajo_stock:
                    mensaje += f"• {producto.nombre} (Stock: {producto.stock}, Mínimo: {producto.stock_minimo})\n"
            
            # Enviar correo
            send_mail(
                subject=f'Reporte diario - {business.name} - {resumen.fecha.strftime("%d/%m/%Y")}',
                message=mensaje,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[business.settings.report_email],
                fail_silently=False,
            )
            
        except Exception as e:
            logger.error(f"Error enviando correo: {e}")


@login_required
def cerrar_dia_page(request):
    """Página para cerrar el día"""
    context = {
        'business': request.user.business,
    }
    return render(request, 'pos/cerrar.html', context)