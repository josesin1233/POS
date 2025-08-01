from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views import View
from django.db import transaction
from django.db.models import Q, F
from decimal import Decimal
import json
import logging

from pos.models import Producto
from pos.utils import validar_codigo_producto

logger = logging.getLogger(__name__)


@login_required
def inventario_view(request):
    """Página principal del inventario"""
    context = {
        'business': request.user.business,
        'user': request.user,
    }
    return render(request, 'inventario/inventario.html', context)


@method_decorator(login_required, name='dispatch')
class InventarioAPIView(View):
    """API para obtener todos los productos del inventario"""
    
    def get(self, request):
        try:
            business = request.user.business
            
            # Parámetros de filtrado opcional
            search = request.GET.get('search', '').strip()
            categoria = request.GET.get('categoria', '').strip()
            stock_bajo = request.GET.get('stock_bajo', '').strip()
            
            # Query base
            productos = Producto.objects.filter(business=business)
            
            # Aplicar filtros
            if search:
                productos = productos.filter(
                    Q(codigo__icontains=search) |
                    Q(nombre__icontains=search) |
                    Q(descripcion__icontains=search)
                )
            
            if categoria:
                productos = productos.filter(categoria__icontains=categoria)
            
            if stock_bajo == 'true':
                productos = productos.filter(stock__lte=F('stock_minimo'), stock_minimo__gt=0)
            
            # Ordenar por nombre
            productos = productos.order_by('nombre')
            
            # Convertir a lista
            productos_data = []
            for producto in productos:
                productos_data.append({
                    'id': producto.id,
                    'codigo': producto.codigo,
                    'nombre': producto.nombre,
                    'precio': float(producto.precio),
                    'stock': producto.stock,
                    'stock_minimo': producto.stock_minimo,
                    'categoria': producto.categoria,
                    'descripcion': producto.descripcion,
                    'tiene_stock_bajo': producto.tiene_stock_bajo,
                    'created_at': producto.created_at.strftime('%d/%m/%Y'),
                    'updated_at': producto.updated_at.strftime('%d/%m/%Y %H:%M')
                })
            
            return JsonResponse({
                'productos': productos_data,
                'total': len(productos_data)
            })
            
        except Exception as e:
            logger.error(f"Error en InventarioAPIView: {e}")
            return JsonResponse({'error': 'Error interno del servidor'}, status=500)


@method_decorator(login_required, name='dispatch')
class AgregarProductoView(View):
    """API para agregar o actualizar productos en el inventario"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            
            # Validar datos requeridos
            codigo = data.get('codigo', '').strip()
            nombre = data.get('nombre', '').strip()
            precio = data.get('precio')
            stock = data.get('stock')
            stock_minimo = data.get('stock_minimo', 0)
            categoria = data.get('categoria', '').strip()
            descripcion = data.get('descripcion', '').strip()
            
            # Validaciones básicas
            if not codigo or not nombre:
                return JsonResponse({'error': 'Código y nombre son requeridos'}, status=400)
            
            # Validar código
            codigo_valido, mensaje_codigo = validar_codigo_producto(codigo)
            if not codigo_valido:
                return JsonResponse({'error': mensaje_codigo}, status=400)
            
            try:
                precio = Decimal(str(precio))
                stock = int(stock)
                stock_minimo = int(stock_minimo)
                
                if precio < 0:
                    return JsonResponse({'error': 'El precio no puede ser negativo'}, status=400)
                if stock < 0:
                    return JsonResponse({'error': 'El stock no puede ser negativo'}, status=400)
                if stock_minimo < 0:
                    return JsonResponse({'error': 'El stock mínimo no puede ser negativo'}, status=400)
                    
            except (TypeError, ValueError, decimal.InvalidOperation):
                return JsonResponse({'error': 'Precio o stock inválido'}, status=400)
            
            business = request.user.business
            
            with transaction.atomic():
                # Verificar si ya existe un producto con el mismo código o nombre
                producto_existente = Producto.objects.filter(
                    business=business
                ).filter(
                    Q(codigo=codigo) | Q(nombre__iexact=nombre)
                ).first()
                
                if producto_existente:
                    # Si existe, actualizar el stock sumando
                    nuevo_stock = producto_existente.stock + stock
                    
                    # Actualizar todos los campos
                    producto_existente.nombre = nombre
                    producto_existente.precio = precio
                    producto_existente.stock = nuevo_stock
                    producto_existente.stock_minimo = stock_minimo
                    producto_existente.categoria = categoria
                    producto_existente.descripcion = descripcion
                    producto_existente.save()
                    
                    return JsonResponse({
                        'mensaje': 'Producto existente actualizado, stock sumado',
                        'producto': {
                            'id': producto_existente.id,
                            'codigo': producto_existente.codigo,
                            'nombre': producto_existente.nombre,
                            'stock_anterior': producto_existente.stock - stock,
                            'stock_agregado': stock,
                            'stock_nuevo': producto_existente.stock
                        }
                    })
                else:
                    # Crear nuevo producto
                    nuevo_producto = Producto.objects.create(
                        business=business,
                        codigo=codigo,
                        nombre=nombre,
                        precio=precio,
                        stock=stock,
                        stock_minimo=stock_minimo,
                        categoria=categoria,
                        descripcion=descripcion,
                        created_by=request.user
                    )
                    
                    return JsonResponse({
                        'mensaje': 'Producto agregado correctamente',
                        'producto': {
                            'id': nuevo_producto.id,
                            'codigo': nuevo_producto.codigo,
                            'nombre': nuevo_producto.nombre,
                            'stock': nuevo_producto.stock
                        }
                    })
                    
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)
        except Exception as e:
            logger.error(f"Error en AgregarProductoView: {e}")
            return JsonResponse({'error': 'Error interno del servidor'}, status=500)


@method_decorator(login_required, name='dispatch')
class ActualizarProductoView(View):
    """API para actualizar un producto existente"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            
            codigo = data.get('codigo', '').strip()
            stock_agregar = data.get('stock_agregar')
            nuevo_precio = data.get('nuevo_precio')
            nuevo_stock_minimo = data.get('stock_minimo')
            nueva_categoria = data.get('categoria', '').strip()
            nueva_descripcion = data.get('descripcion', '').strip()
            
            if not codigo:
                return JsonResponse({'error': 'Código requerido'}, status=400)
            
            business = request.user.business
            
            # Buscar el producto
            producto = Producto.objects.filter(
                business=business,
                codigo=codigo
            ).first()
            
            if not producto:
                return JsonResponse({'error': 'Producto no encontrado'}, status=404)
            
            with transaction.atomic():
                # Actualizar stock si se especifica
                if stock_agregar is not None:
                    try:
                        stock_agregar = int(stock_agregar)
                        if stock_agregar < 0:
                            return JsonResponse({'error': 'No se puede agregar stock negativo'}, status=400)
                        producto.agregar_stock(stock_agregar)
                    except (TypeError, ValueError):
                        return JsonResponse({'error': 'Stock a agregar inválido'}, status=400)
                
                # Actualizar precio si se especifica
                if nuevo_precio is not None:
                    try:
                        nuevo_precio = Decimal(str(nuevo_precio))
                        if nuevo_precio < 0:
                            return JsonResponse({'error': 'El precio no puede ser negativo'}, status=400)
                        producto.precio = nuevo_precio
                    except (TypeError, ValueError, decimal.InvalidOperation):
                        return JsonResponse({'error': 'Precio inválido'}, status=400)
                
                # Actualizar stock mínimo si se especifica
                if nuevo_stock_minimo is not None:
                    try:
                        nuevo_stock_minimo = int(nuevo_stock_minimo)
                        if nuevo_stock_minimo < 0:
                            return JsonResponse({'error': 'El stock mínimo no puede ser negativo'}, status=400)
                        producto.stock_minimo = nuevo_stock_minimo
                    except (TypeError, ValueError):
                        return JsonResponse({'error': 'Stock mínimo inválido'}, status=400)
                
                # Actualizar campos de texto
                if nueva_categoria:
                    producto.categoria = nueva_categoria
                
                if nueva_descripcion:
                    producto.descripcion = nueva_descripcion
                
                producto.save()
                
                return JsonResponse({
                    'mensaje': 'Producto actualizado correctamente',
                    'producto': {
                        'codigo': producto.codigo,
                        'nombre': producto.nombre,
                        'precio': float(producto.precio),
                        'stock': producto.stock,
                        'stock_minimo': producto.stock_minimo,
                        'categoria': producto.categoria,
                        'tiene_stock_bajo': producto.tiene_stock_bajo
                    }
                })
                
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)
        except Exception as e:
            logger.error(f"Error en ActualizarProductoView: {e}")
            return JsonResponse({'error': 'Error interno del servidor'}, status=500)


@method_decorator(login_required, name='dispatch')
class ProductosStockBajoView(View):
    """API para obtener productos con stock bajo"""
    
    def get(self, request):
        try:
            business = request.user.business
            
            productos_bajo_stock = Producto.objects.filter(
                business=business,
                stock__lte=F('stock_minimo'),
                stock_minimo__gt=0
            ).order_by('stock')
            
            productos_data = []
            for producto in productos_bajo_stock:
                productos_data.append({
                    'id': producto.id,
                    'codigo': producto.codigo,
                    'nombre': producto.nombre,
                    'stock': producto.stock,
                    'stock_minimo': producto.stock_minimo,
                    'categoria': producto.categoria,
                    'precio': float(producto.precio),
                    'diferencia': producto.stock_minimo - producto.stock
                })
            
            return JsonResponse({
                'productos': productos_data,
                'total': len(productos_data)
            })
            
        except Exception as e:
            logger.error(f"Error en ProductosStockBajoView: {e}")
            return JsonResponse({'error': 'Error interno del servidor'}, status=500)


@method_decorator(login_required, name='dispatch')
class EliminarProductoView(View):
    """API para eliminar un producto (solo si no tiene ventas)"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            producto_id = data.get('producto_id')
            
            if not producto_id:
                return JsonResponse({'error': 'ID del producto requerido'}, status=400)
            
            business = request.user.business
            
            producto = get_object_or_404(Producto, id=producto_id, business=business)
            
            # Verificar si el producto tiene ventas
            from pos.models import VentaDetalle
            tiene_ventas = VentaDetalle.objects.filter(producto=producto).exists()
            
            if tiene_ventas:
                return JsonResponse({
                    'error': 'No se puede eliminar un producto que tiene ventas registradas'
                }, status=400)
            
            nombre_producto = producto.nombre
            producto.delete()
            
            return JsonResponse({
                'mensaje': f'Producto "{nombre_producto}" eliminado correctamente'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'JSON inválido'}, status=400)
        except Exception as e:
            logger.error(f"Error en EliminarProductoView: {e}")
            return JsonResponse({'error': 'Error interno del servidor'}, status=500)


@method_decorator(login_required, name='dispatch')
class BuscarProductoView(View):
    """API para buscar un producto específico por código o nombre"""
    
    def get(self, request):
        try:
            codigo = request.GET.get('codigo', '').strip()
            nombre = request.GET.get('nombre', '').strip()
            
            if not codigo and not nombre:
                return JsonResponse({'error': 'Código o nombre requerido'}, status=400)
            
            business = request.user.business
            
            if codigo:
                producto = Producto.objects.filter(business=business, codigo=codigo).first()
            else:
                producto = Producto.objects.filter(business=business, nombre__iexact=nombre).first()
            
            if not producto:
                return JsonResponse({'error': 'Producto no encontrado'}, status=404)
            
            return JsonResponse({
                'producto': {
                    'id': producto.id,
                    'codigo': producto.codigo,
                    'nombre': producto.nombre,
                    'precio': float(producto.precio),
                    'stock': producto.stock,
                    'stock_minimo': producto.stock_minimo,
                    'categoria': producto.categoria,
                    'descripcion': producto.descripcion,
                    'tiene_stock_bajo': producto.tiene_stock_bajo
                }
            })
            
        except Exception as e:
            logger.error(f"Error en BuscarProductoView: {e}")
            return JsonResponse({'error': 'Error interno del servidor'}, status=500)


@method_decorator(login_required, name='dispatch')
class CategoriasView(View):
    """API para obtener todas las categorías disponibles"""
    
    def get(self, request):
        try:
            business = request.user.business
            
            categorias = Producto.objects.filter(
                business=business,
                categoria__isnull=False
            ).exclude(
                categoria=''
            ).values_list('categoria', flat=True).distinct().order_by('categoria')
            
            return JsonResponse({
                'categorias': list(categorias)
            })
            
        except Exception as e:
            logger.error(f"Error en CategoriasView: {e}")
            return JsonResponse({'error': 'Error interno del servidor'}, status=500)