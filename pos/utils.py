from decimal import Decimal, ROUND_HALF_UP
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def redondear_personalizado(monto):
    """
    Función de redondeo personalizado para el POS
    Si los centavos son >= 0.50, redondea hacia arriba
    Si los centavos son < 0.50, redondea hacia abajo
    """
    if isinstance(monto, (int, float)):
        monto = Decimal(str(monto))
    
    parte_entera = int(monto)
    centavos = monto - parte_entera
    
    if centavos >= Decimal('0.50'):
        return Decimal(str(parte_entera + 1))
    else:
        return Decimal(str(parte_entera))


def calcular_cambio(total_venta, monto_pagado):
    """Calcula el cambio de una venta"""
    total = Decimal(str(total_venta))
    pagado = Decimal(str(monto_pagado))
    
    if pagado < total:
        return None, "El monto pagado es insuficiente"
    
    cambio = pagado - total
    return float(cambio), None


def validar_stock_suficiente(business, productos_a_vender):
    """
    Valida que haya stock suficiente para todos los productos
    productos_a_vender: lista de diccionarios [{'codigo': 'ABC', 'cantidad': 2}, ...]
    """
    from .models import Producto
    
    productos_sin_stock = []
    
    for item in productos_a_vender:
        codigo = item.get('codigo')
        cantidad = item.get('cantidad', 0)
        
        try:
            producto = Producto.objects.get(business=business, codigo=codigo)
            if producto.stock < cantidad:
                productos_sin_stock.append({
                    'codigo': producto.codigo,
                    'nombre': producto.nombre,
                    'stock_disponible': producto.stock,
                    'cantidad_solicitada': cantidad
                })
        except Producto.DoesNotExist:
            productos_sin_stock.append({
                'codigo': codigo,
                'nombre': 'Producto no encontrado',
                'stock_disponible': 0,
                'cantidad_solicitada': cantidad
            })
    
    return len(productos_sin_stock) == 0, productos_sin_stock


def obtener_productos_stock_bajo(business):
    """Obtiene productos con stock bajo o agotado"""
    from .models import Producto
    
    productos_bajo = Producto.objects.filter(
        business=business,
        stock__lte=models.F('stock_minimo'),
        stock_minimo__gt=0
    ).values('codigo', 'nombre', 'stock', 'stock_minimo')
    
    return list(productos_bajo)


def calcular_estadisticas_ventas(business, fecha_inicio=None, fecha_fin=None):
    """
    Calcula estadísticas de ventas para un período
    Si no se especifican fechas, usa el día actual
    """
    from .models import Venta, VentaDetalle
    
    if not fecha_inicio:
        fecha_inicio = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if not fecha_fin:
        fecha_fin = timezone.now().replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Estadísticas básicas
    ventas = Venta.objects.filter(
        business=business,
        fecha__range=[fecha_inicio, fecha_fin]
    )
    
    stats = ventas.aggregate(
        total_ventas=Sum('total_venta'),
        numero_ventas=Count('id'),
        venta_promedio=Sum('total_venta') / Count('id') if ventas.exists() else 0
    )
    
    # Productos más vendidos
    productos_vendidos = VentaDetalle.objects.filter(
        venta__business=business,
        venta__fecha__range=[fecha_inicio, fecha_fin]
    ).values(
        'codigo_producto', 'nombre_producto'
    ).annotate(
        cantidad_total=Sum('cantidad_vendida'),
        ingresos_total=Sum('total')
    ).order_by('-cantidad_total')[:10]
    
    return {
        'total_ventas': stats['total_ventas'] or 0,
        'numero_ventas': stats['numero_ventas'],
        'venta_promedio': stats['venta_promedio'] or 0,
        'productos_mas_vendidos': list(productos_vendidos),
        'periodo': {
            'inicio': fecha_inicio,
            'fin': fecha_fin
        }
    }


def generar_reporte_diario(business, fecha=None):
    """Genera un reporte completo del día"""
    if not fecha:
        fecha = timezone.now().date()
    
    fecha_inicio = timezone.datetime.combine(fecha, timezone.datetime.min.time())
    fecha_fin = timezone.datetime.combine(fecha, timezone.datetime.max.time())
    
    # Hacer timezone-aware
    fecha_inicio = timezone.make_aware(fecha_inicio)
    fecha_fin = timezone.make_aware(fecha_fin)
    
    # Estadísticas del día
    stats = calcular_estadisticas_ventas(business, fecha_inicio, fecha_fin)
    
    # Productos con stock bajo
    productos_bajo_stock = obtener_productos_stock_bajo(business)
    
    # Ventas del día
    from .models import Venta
    ventas_del_dia = Venta.objects.filter(
        business=business,
        fecha__range=[fecha_inicio, fecha_fin]
    ).select_related('vendedor').prefetch_related('productos__producto')
    
    return {
        'fecha': fecha,
        'business': business,
        'estadisticas': stats,
        'productos_bajo_stock': productos_bajo_stock,
        'ventas': ventas_del_dia,
        'resumen': {
            'total_ingresos': stats['total_ventas'],
            'total_ventas': stats['numero_ventas'],
            'productos_vendidos': sum(p['cantidad_total'] for p in stats['productos_mas_vendidos']),
            'productos_con_stock_bajo': len(productos_bajo_stock)
        }
    }


def enviar_reporte_por_correo(business, reporte_data, email_destino=None):
    """Envía un reporte por correo electrónico"""
    try:
        if not email_destino:
            if hasattr(business, 'settings') and business.settings.report_email:
                email_destino = business.settings.report_email
            else:
                return False, "No hay email configurado para reportes"
        
        fecha = reporte_data['fecha']
        stats = reporte_data['estadisticas']
        productos_bajo = reporte_data['productos_bajo_stock']
        
        # Construir el mensaje
        mensaje = f"""
🧾 REPORTE DIARIO - {business.name.upper()}
📅 Fecha: {fecha.strftime('%d/%m/%Y')}

💰 RESUMEN DE VENTAS:
• Total de ingresos: ${stats['total_ventas']:,.2f}
• Número de ventas: {stats['numero_ventas']}
• Venta promedio: ${stats['venta_promedio']:,.2f}

🛍️ PRODUCTOS MÁS VENDIDOS:
"""
        
        for i, producto in enumerate(stats['productos_mas_vendidos'][:5], 1):
            mensaje += f"{i}. {producto['nombre_producto']} - {producto['cantidad_total']} unidades (${producto['ingresos_total']:,.2f})\n"
        
        if productos_bajo:
            mensaje += f"\n⚠️ PRODUCTOS CON STOCK BAJO ({len(productos_bajo)}):\n"
            for producto in productos_bajo[:10]:  # Máximo 10 productos
                mensaje += f"• {producto['nombre']} - Stock: {producto['stock']} (Mínimo: {producto['stock_minimo']})\n"
        
        mensaje += f"\n---\nReporte generado automáticamente por Sistema POS\n{timezone.now().strftime('%d/%m/%Y %H:%M')}"
        
        # Enviar correo
        send_mail(
            subject=f'📊 Reporte Diario - {business.name} - {fecha.strftime("%d/%m/%Y")}',
            message=mensaje,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email_destino],
            fail_silently=False,
        )
        
        return True, "Reporte enviado exitosamente"
        
    except Exception as e:
        logger.error(f"Error enviando reporte por correo: {e}")
        return False, f"Error enviando correo: {str(e)}"


def limpiar_carritos_temporales(business, dias_antiguedad=7):
    """Limpia carritos temporales antiguos"""
    from .models import CarritoTemporal
    
    fecha_limite = timezone.now() - timezone.timedelta(days=dias_antiguedad)
    
    carritos_eliminados = CarritoTemporal.objects.filter(
        business=business,
        fecha_agregado__lt=fecha_limite
    ).delete()
    
    return carritos_eliminados[0] if carritos_eliminados[0] else 0


def validar_codigo_producto(codigo):
    """Valida que el código del producto sea válido"""
    if not codigo or not isinstance(codigo, str):
        return False, "Código inválido"
    
    codigo = codigo.strip()
    
    if len(codigo) < 1:
        return False, "El código no puede estar vacío"
    
    if len(codigo) > 50:
        return False, "El código es demasiado largo (máximo 50 caracteres)"
    
    # Caracteres permitidos: letras, números, guiones, puntos
    import re
    if not re.match(r'^[a-zA-Z0-9\-\.]+$', codigo):
        return False, "El código solo puede contener letras, números, guiones y puntos"
    
    return True, "Código válido"


def formatear_moneda(monto, moneda='MXN'):
    """Formatea una cantidad como moneda"""
    if isinstance(monto, str):
        try:
            monto = float(monto)
        except:
            return "0.00"
    
    if moneda == 'MXN':
        return f"${monto:,.2f}"
    else:
        return f"{monto:,.2f} {moneda}"


def obtener_usuario_activos_negocio(business):
    """Obtiene la lista de usuarios activos del negocio"""
    from accounts.models import UserSession
    
    cutoff_time = timezone.now() - timezone.timedelta(minutes=30)
    
    sesiones_activas = UserSession.objects.filter(
        user__business=business,
        last_activity__gte=cutoff_time
    ).select_related('user').order_by('-last_activity')
    
    usuarios_activos = []
    for sesion in sesiones_activas:
        usuarios_activos.append({
            'username': sesion.user.username,
            'nombre_completo': sesion.user.get_full_name(),
            'ultima_actividad': sesion.last_activity,
            'ip_address': sesion.ip_address,
            'tiempo_activo': timezone.now() - sesion.created_at
        })
    
    return usuarios_activos


class ReporteExportador:
    """Clase para exportar reportes en diferentes formatos"""
    
    def __init__(self, business):
        self.business = business
    
    def exportar_ventas_csv(self, fecha_inicio, fecha_fin):
        """Exporta ventas a CSV"""
        import csv
        from io import StringIO
        from .models import Venta
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Headers
        writer.writerow([
            'Fecha', 'ID Venta', 'Vendedor', 'Total', 
            'Monto Pagado', 'Cambio', 'Productos'
        ])
        
        # Datos
        ventas = Venta.objects.filter(
            business=self.business,
            fecha__range=[fecha_inicio, fecha_fin]
        ).select_related('vendedor').prefetch_related('productos')
        
        for venta in ventas:
            productos_str = '; '.join([
                f"{p.nombre_producto} x{p.cantidad_vendida}" 
                for p in venta.productos.all()
            ])
            
            writer.writerow([
                venta.fecha.strftime('%d/%m/%Y %H:%M'),
                venta.id,
                venta.vendedor.get_full_name() if venta.vendedor else 'N/A',
                float(venta.total_venta),
                float(venta.monto_pagado),
                float(venta.cambio),
                productos_str
            ])
        
        return output.getvalue()