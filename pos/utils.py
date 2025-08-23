from decimal import Decimal
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

def redondear_personalizado(monto):
    """
    Función de redondeo personalizado para el POS
    Si los centavos son >= 0.5, redondea hacia arriba
    Si los centavos son < 0.5, redondea hacia abajo
    """
    if isinstance(monto, (int, float)):
        monto = Decimal(str(monto))
    
    parte_entera = int(monto)
    centavos = monto - parte_entera
    
    if centavos >= Decimal('0.5'):
        return Decimal(str(parte_entera + 1))
    else:
        return Decimal(str(parte_entera))

def calcular_estadisticas_ventas(ventas):
    """Calcula estadísticas básicas de una lista de ventas"""
    if not ventas:
        return {
            'total_ventas': 0,
            'numero_ventas': 0,
            'venta_promedio': 0,
            'productos_vendidos': 0
        }
    
    total_ventas = sum(venta.total_venta for venta in ventas)
    numero_ventas = len(ventas)
    venta_promedio = total_ventas / numero_ventas if numero_ventas > 0 else 0
    
    return {
        'total_ventas': float(total_ventas),
        'numero_ventas': numero_ventas,
        'venta_promedio': float(venta_promedio),
        'productos_vendidos': 0  # Simplificado por ahora
    }

def generar_reporte_diario(business_id, fecha=None):
    """Genera un reporte diario básico"""
    if fecha is None:
        fecha = timezone.now().date()
    
    return {
        'fecha': fecha.strftime('%Y-%m-%d'),
        'business': 'Dulcería',
        'estadisticas': {
            'total_ingresos': 0,
            'total_ventas': 0,
            'venta_promedio': 0
        },
        'productos_bajo_stock': []
    }

def enviar_reporte_por_correo(email, reporte):
    """Envía un reporte por correo electrónico"""
    try:
        mensaje = f"""
        Reporte Diario - {reporte.get('fecha', 'Hoy')}
        
        Total de ventas: ${reporte.get('estadisticas', {}).get('total_ingresos', 0):,.2f}
        Número de ventas: {reporte.get('estadisticas', {}).get('total_ventas', 0)}
        
        Saludos,
        Sistema POS
        """
        
        send_mail(
            subject=f'Reporte Diario - {reporte.get("fecha", "Hoy")}',
            message=mensaje,
            from_email=getattr(settings, 'EMAIL_HOST_USER', 'noreply@dulceriapos.com'),
            recipient_list=[email],
            fail_silently=True,
        )
        return True
    except Exception as e:
        print(f"Error enviando correo: {e}")
        return False