from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from pos.models import Producto
from accounts.models import Business
import json
import logging

logger = logging.getLogger(__name__)

def inventario_view(request):
    """Vista principal del inventario"""
    try:
        productos = Producto.objects.all().order_by('codigo')
        context = {
            'productos': productos,
            'total_productos': productos.count()
        }
        return render(request, 'inventario/inventario.html', context)
    except Exception as e:
        logger.error(f"Error en inventario_view: {e}")
        return render(request, 'inventario/inventario.html', {'productos': [], 'error': str(e)})

@csrf_exempt
@require_http_methods(["POST"])
def agregar_producto(request):
    """API para agregar productos"""
    try:
        # Parsear JSON
        data = json.loads(request.body)
        
        # Validar campos requeridos
        required_fields = ['codigo', 'nombre', 'precio']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({
                    'success': False, 
                    'error': f'Campo requerido: {field}'
                }, status=400)
        
        # Verificar si el código ya existe
        if Producto.objects.filter(codigo=data['codigo']).exists():
            return JsonResponse({
                'success': False,
                'error': f'El código {data["codigo"]} ya existe'
            }, status=400)
        
        # Obtener business (usar ID 1 por defecto)
        business = Business.objects.get(id=1)
        
        # Crear producto
        producto = Producto.objects.create(
            codigo=data['codigo'].upper(),
            nombre=data['nombre'],
            precio=float(data['precio']),
            stock=int(data.get('stock', 0)),
            business=business
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Producto agregado exitosamente',
            'producto': {
                'id': producto.id,
                'codigo': producto.codigo,
                'nombre': producto.nombre,
                'precio': str(producto.precio),
                'stock': producto.stock
            }
        })
        
    except Exception as e:
        logger.error(f"Error agregando producto: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Error interno: {str(e)}'
        }, status=500)

@csrf_exempt
def inventario_api(request):
    """API para obtener todos los productos"""
    try:
        productos = Producto.objects.all().order_by('codigo')
        productos_data = []
        
        for producto in productos:
            productos_data.append({
                'id': producto.id,
                'codigo': producto.codigo,
                'nombre': producto.nombre,
                'precio': float(producto.precio),
                'stock': producto.stock
            })
        
        return JsonResponse(productos_data, safe=False)
        
    except Exception as e:
        logger.error(f"Error en inventario_api: {e}")
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt  
def poco_stock_api(request):
    """API para productos con poco stock"""
    try:
        productos = Producto.objects.filter(stock__lt=10).order_by('stock')
        productos_data = []
        
        for producto in productos:
            productos_data.append({
                'id': producto.id,
                'codigo': producto.codigo,
                'nombre': producto.nombre,
                'stock': producto.stock,
                'precio': float(producto.precio)
            })
        
        return JsonResponse(productos_data, safe=False)
        
    except Exception as e:
        logger.error(f"Error en poco_stock_api: {e}")
        return JsonResponse({'error': str(e)}, status=500)
@csrf_exempt
@require_http_methods(["POST"])
def actualizar_producto(request):
    """API para actualizar productos"""
    try:
        data = json.loads(request.body)
        
        # Validar que venga el código del producto
        codigo = data.get('codigo')
        if not codigo:
            return JsonResponse({
                'success': False,
                'error': 'Código de producto requerido'
            }, status=400)
        
        # Buscar el producto
        try:
            producto = Producto.objects.get(codigo=codigo)
        except Producto.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Producto con código {codigo} no encontrado'
            }, status=404)
        
        # Actualizar campos si vienen en los datos
        if 'stock_agregar' in data:
            stock_agregar = int(data['stock_agregar'])
            producto.stock += stock_agregar
        
        if 'nuevo_precio' in data:
            producto.precio = float(data['nuevo_precio'])
        
        if 'stock_minimo' in data:
            producto.stock_minimo = int(data['stock_minimo'])
        
        # Guardar cambios
        producto.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Producto actualizado exitosamente',
            'producto': {
                'id': producto.id,
                'codigo': producto.codigo,
                'nombre': producto.nombre,
                'precio': str(producto.precio),
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