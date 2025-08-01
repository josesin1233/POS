from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta, date
import json
import csv
import logging

from pos.models import Venta, VentaDetalle, ResumenDiario
from pos.utils import calcular_estadisticas_ventas, generar_reporte_diario, enviar_reporte_por_correo

logger = logging.getLogger(__name__)


@login_required
def ventas_view(request):
    """Página principal de registro de ventas"""
    context = {
        'business': request.user.business,
        'user': request.user,
    }
    return render(request, 'ventas/registro.html', context)


@method_decorator(login_required, name='dispatch')
class VentasAPIView(View):
    """API para obtener ventas con filtros"""
    
    def get(self, request):
        try:
            business = request.user.business
            
            # Parámetros de filtrado
            dia = request.GET.get('dia')
            mes = request.GET.get('mes')
            anio = request.GET.get('anio')
            fecha_inicio = request.GET.get('fecha_inicio')
            fecha_fin = request.GET.get('fecha_fin')
            vendedor_id = request.GET.get('vendedor')
            
            # Query base
            ventas = Venta.objects.filter(business=business)
            
            # Aplicar filtros de fecha
            if dia:
                try:
                    fecha = datetime.strptime(dia, "%Y-%m-%d").date()
                    inicio = timezone.make_aware(datetime.combine(fecha, datetime.min.time()))
                    fin = timezone.make_aware(datetime.combine(fecha, datetime.max.time()))
                    ventas = ventas.filter(fecha__range=[inicio, fin])
                except ValueError:
                    return JsonResponse({'error': 'Formato de fecha incorrecto para día. Usa YYYY-MM-DD'}, status=400)
            
            elif mes:
                try:
                    fecha = datetime.strptime(mes, "%Y-%m")
                    inicio = timezone.make_aware(datetime(fecha.year, fecha.month, 1))
                    if fecha.month == 12:
                        fin = timezone.make_aware(datetime(fecha.year + 1, 1, 1))
                    else:
                        fin = timezone.make_aware(datetime(fecha.year, fecha.month + 1, 1))
                    ventas = ventas.filter(fecha__range=[inicio, fin])
                except ValueError:
                    return JsonResponse({'error': 'Formato incorrecto para mes. Usa YYYY-MM'}, status=400)
            
            elif anio:
                try:
                    year = int(anio)
                    inicio = timezone.make_aware(datetime(year, 1, 1))
                    fin = timezone.make_aware(datetime(year + 1, 1, 1))
                    ventas = ventas.filter(fecha__range=[inicio, fin])
                except ValueError:
                    return JsonResponse({'error': 'Año inválido'}, status=400)
            
            elif fecha_inicio and fecha_fin:
                try:
                    inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d")
                    fin = datetime.strptime(fecha_fin, "%Y-%m-%d")
                    inicio = timezone.make_aware(datetime.combine(inicio.date(), datetime.min.time()))
                    fin = timezone.make_aware(datetime.combine(fin.date(), datetime.max.time()))
                    ventas = ventas.filter(fecha__range=[inicio, fin])
                except ValueError:
                    return JsonResponse({'error': 'Formato de fechas incorrecto'}, status=400)
            
            # Filtro por vendedor
            if vendedor_id:
                try:
                    vendedor_id = int(vendedor_id)
                    ventas = ventas.filter(vendedor_id=vendedor_id)
                except ValueError:
                    return JsonResponse({'error': 'ID de vendedor inválido'}, status=400)
            
            # Ordenar y paginar
            ventas = ventas.select_related('vendedor').prefetch_related('productos__producto').order_by('-fecha')
            
            # Limitar resultados para evitar sobrecarga
            limit = min(int(request.GET.get('limit', 100)), 500)
            ventas = ventas[:limit]
            
            # Convertir a lista
            ventas_data = []
            for venta in ventas:
                productos_data = []
                for detalle in venta.productos.all():
                    productos_data.append({
                        'codigo_producto': detalle.codigo_producto,
                        'nombre_producto': detalle.nombre_producto,
                        'cantidad_vendida': detalle.cantidad_vendida,
                        'precio_unitario': float(detalle.precio_unitario),
                        'total': float(detalle.total)
                    })
                
                ventas_data.append({
                    'id': venta.id,
                    'fecha': venta.fecha.isoformat(),
                    'fecha_formato': venta.fecha.strftime('%d/%m/%Y %H:%M'),
                    'total_venta': float(venta.total_venta),
                    'monto_pagado': float(venta.monto_pagado),
                    'cambio': float(venta.cambio),
                    'vendedor': venta.vendedor.get_full_name() if venta.vendedor else 'N/A',
                    'productos': productos_data,
                    'numero_productos': len(productos_data),
                    'notas': venta.notas
                })
            
            # Calcular totales
            total_ventas = sum(venta['total_venta'] for venta in ventas_data)
            numero_ventas = len(ventas_data)
            
            return JsonResponse({
                'ventas': ventas_data,
                'resumen': {
                    'total_ventas': total_ventas,
                    'numero_ventas': numero_ventas,
                    'venta_promedio': total_ventas / numero_ventas if numero_ventas > 0 else 0
                }
            })
            
        except Exception as e:
            logger.error(f"Error en VentasAPIView: {e}")
            return JsonResponse({'error': 'Error interno del servidor'}, status=500)


@method_decorator(login_required, name='dispatch')
class EstadisticasVentasView(View):
    """API para obtener estadísticas de ventas"""
    
    def get(self, request):
        try:
            business = request.user.business
            
            # Parámetros
            periodo = request.GET.get('periodo', 'hoy')  # hoy, semana, mes, año
            
            ahora = timezone.now()
            
            if periodo == 'hoy':
                inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
                fin = ahora
            elif periodo == 'semana':
                inicio = ahora - timedelta(days=7)
            elif periodo == 'mes':
                inicio = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                fin = ahora
            elif periodo == 'año':
                inicio = ahora.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                fin = ahora
            else:
                return JsonResponse({'error': 'Período inválido'}, status=400)
            
            # Calcular estadísticas
            stats = calcular_estadisticas_ventas(business, inicio, fin)
            
            # Ventas por día (últimos 7 días)
            ventas_por_dia = []
            for i in range(7):
                fecha = (ahora - timedelta(days=i)).date()
                total_dia = Venta.objects.filter(
                    business=business,
                    fecha__date=fecha
                ).aggregate(total=Sum('total_venta'))['total'] or 0
                
                ventas_por_dia.append({
                    'fecha': fecha.strftime('%d/%m'),
                    'total': float(total_dia)
                })
            
            ventas_por_dia.reverse()  # Ordenar cronológicamente
            
            # Productos más vendidos (top 10)
            productos_top = stats['productos_mas_vendidos'][:10]
            
            # Vendedores con más ventas
            vendedores_stats = Venta.objects.filter(
                business=business,
                fecha__range=[inicio, fin],
                vendedor__isnull=False
            ).values(
                'vendedor__first_name', 'vendedor__last_name'
            ).annotate(
                total_ventas=Sum('total_venta'),
                numero_ventas=Count('id')
            ).order_by('-total_ventas')[:5]
            
            return JsonResponse({
                'periodo': periodo,
                'estadisticas_generales': {
                    'total_ventas': float(stats['total_ventas']),
                    'numero_ventas': stats['numero_ventas'],
                    'venta_promedio': float(stats['venta_promedio'])
                },
                'ventas_por_dia': ventas_por_dia,
                'productos_mas_vendidos': productos_top,
                'vendedores_top': list(vendedores_stats),
                'fecha_inicio': inicio.strftime('%d/%m/%Y'),
                'fecha_fin': fin.strftime('%d/%m/%Y')
            })
            
        except Exception as e:
            logger.error(f"Error en EstadisticasVentasView: {e}")
            return JsonResponse({'error': 'Error interno del servidor'}, status=500)


@method_decorator(login_required, name='dispatch')
class ReporteDiarioView(View):
    """Vista para generar y enviar reportes diarios"""
    
    def get(self, request):
        """Obtener reporte diario"""
        try:
            business = request.user.business
            fecha_str = request.GET.get('fecha')
            
            if fecha_str:
                try:
                    fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                except ValueError:
                    return JsonResponse({'error': 'Formato de fecha inválido'}, status=400)
            else:
                fecha = timezone.now().date()
            
            # Generar reporte
            reporte = generar_reporte_diario(business, fecha)
            
            # Formatear datos para JSON
            ventas_data = []
            for venta in reporte['ventas']:
                ventas_data.append({
                    'id': venta.id,
                    'fecha': venta.fecha.strftime('%H:%M'),
                    'total': float(venta.total_venta),
                    'vendedor': venta.vendedor.get_full_name() if venta.vendedor else 'N/A',
                    'productos_count': venta.productos.count()
                })
            
            return JsonResponse({
                'fecha': fecha.strftime('%d/%m/%Y'),
                'business': reporte['business'].name,
                'estadisticas': {
                    'total_ingresos': float(reporte['estadisticas']['total_ventas']),
                    'total_ventas': reporte['estadisticas']['numero_ventas'],
                    'venta_promedio': float(reporte['estadisticas']['venta_promedio']),
                    'productos_mas_vendidos': reporte['estadisticas']['productos_mas_vendidos'][:5]
                },
                'productos_bajo_stock': reporte['productos_bajo_stock'],
                'ventas': ventas_data,
                'resumen': reporte['resumen']
            })
            
        except Exception as e:
            logger.error(f"Error en ReporteDiarioView GET: {e}")
            return JsonResponse({'error': 'Error interno del servidor'}, status=500)
    
    def post(self, request):
        """Enviar reporte diario por correo"""
        try:
            data = json.loads(request.body)
            fecha_str = data.get('fecha')
            email_destino = data.get('email')
            
            business = request.user.business
            
            if fecha_str:
                try:
                    fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                except ValueError:
                    return JsonResponse({'error': 'Formato de fecha inválido'}, status=400)
            else:
                fecha = timezone.now().date()
            
            # Generar reporte
            reporte = generar_reporte_diario(business, fecha)
            
            # Enviar por correo
            enviado, mensaje = enviar_reporte_por_correo(business, reporte, email_destino)
            
            if enviado:
                return JsonResponse({'mensaje': mensaje})
            else:
                return JsonResponse({'error': mensaje}, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)
        except Exception as e:
            logger.error(f"Error en ReporteDiarioView POST: {e}")
            return JsonResponse({'error': 'Error interno del servidor'}, status=500)


@method_decorator(login_required, name='dispatch')
class ExportarVentasView(View):
    """Vista para exportar ventas a CSV"""
    
    def get(self, request):
        try:
            business = request.user.business
            
            # Parámetros
            fecha_inicio = request.GET.get('fecha_inicio')
            fecha_fin = request.GET.get('fecha_fin')
            formato = request.GET.get('formato', 'csv')
            
            if not fecha_inicio or not fecha_fin:
                return JsonResponse({'error': 'Fechas de inicio y fin requeridas'}, status=400)
            
            try:
                inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d')
                fin = datetime.strptime(fecha_fin, '%Y-%m-%d')
                inicio = timezone.make_aware(datetime.combine(inicio.date(), datetime.min.time()))
                fin = timezone.make_aware(datetime.combine(fin.date(), datetime.max.time()))
            except ValueError:
                return JsonResponse({'error': 'Formato de fechas inválido'}, status=400)
            
            if formato == 'csv':
                return self._exportar_csv(business, inicio, fin)
            else:
                return JsonResponse({'error': 'Formato no soportado'}, status=400)
                
        except Exception as e:
            logger.error(f"Error en ExportarVentasView: {e}")
            return JsonResponse({'error': 'Error interno del servidor'}, status=500)
    
    def _exportar_csv(self, business, fecha_inicio, fecha_fin):
        """Exporta ventas a CSV"""
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="ventas_{business.name}_{fecha_inicio.strftime("%Y%m%d")}_{fecha_fin.strftime("%Y%m%d")}.csv"'
        
        # BOM para UTF-8 (para Excel)
        response.write('\ufeff')
        
        writer = csv.writer(response)
        
        # Headers
        writer.writerow([
            'Fecha', 'Hora', 'ID Venta', 'Vendedor', 'Total Venta', 
            'Monto Pagado', 'Cambio', 'Código Producto', 'Producto', 
            'Cantidad', 'Precio Unitario', 'Total Producto'
        ])
        
        # Datos
        ventas = Venta.objects.filter(
            business=business,
            fecha__range=[fecha_inicio, fecha_fin]
        ).select_related('vendedor').prefetch_related('productos')
        
        for venta in ventas:
            for detalle in venta.productos.all():
                writer.writerow([
                    venta.fecha.strftime('%d/%m/%Y'),
                    venta.fecha.strftime('%H:%M:%S'),
                    venta.id,
                    venta.vendedor.get_full_name() if venta.vendedor else 'N/A',
                    float(venta.total_venta),
                    float(venta.monto_pagado),
                    float(venta.cambio),
                    detalle.codigo_producto,
                    detalle.nombre_producto,
                    detalle.cantidad_vendida,
                    float(detalle.precio_unitario),
                    float(detalle.total)
                ])
        
        return response


@method_decorator(login_required, name='dispatch')
class ResumenDiarioAPIView(View):
    """API para manejar resúmenes diarios"""
    
    def get(self, request):
        """Obtener resumen diario"""
        try:
            business = request.user.business
            fecha_str = request.GET.get('fecha')
            
            if fecha_str:
                try:
                    fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
                except ValueError:
                    return JsonResponse({'error': 'Formato de fecha inválido'}, status=400)
            else:
                fecha = timezone.now().date()
            
            resumen = ResumenDiario.objects.filter(
                business=business,
                fecha=fecha
            ).first()
            
            if not resumen:
                # Crear resumen si no existe
                resumen = ResumenDiario.obtener_o_crear_hoy(business)
                resumen.fecha = fecha
                resumen.save()
                resumen.actualizar_totales()
            
            return JsonResponse({
                'fecha': resumen.fecha.strftime('%d/%m/%Y'),
                'total_ventas': float(resumen.total_ventas),
                'numero_ventas': resumen.numero_ventas,
                'productos_vendidos': resumen.productos_vendidos,
                'dia_cerrado': resumen.dia_cerrado,
                'fecha_cierre': resumen.fecha_cierre.isoformat() if resumen.fecha_cierre else None,
                'cerrado_por': resumen.cerrado_por.get_full_name() if resumen.cerrado_por else None
            })
            
        except Exception as e:
            logger.error(f"Error en ResumenDiarioAPIView GET: {e}")
            return JsonResponse({'error': 'Error interno del servidor'}, status=500)