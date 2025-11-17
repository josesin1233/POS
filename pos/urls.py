"""
URLs del módulo POS - Sistema para Dulcerías México
"""

from django.urls import path
from . import views

app_name = 'pos'

# URLs esenciales para funcionamiento básico
urlpatterns = [
    # ========================
    # VISTAS PRINCIPALES (USADAS)
    # ========================
    
    # Página principal (Demo público)
    path('pos/', views.index_view, name='index'),
    
    # POS completo (requiere login)
    path('punto_de_venta/', views.pos_view, name='punto_de_venta'),
    
    # Inventario
    path('inventario/', views.inventario_view, name='inventario'),
    
    # ========================
    # API PRODUCTOS (USADAS)
    # ========================
    
    # Información del negocio del usuario
    path('business/info/', views.get_business_info, name='get_business_info'),
    
    # Búsqueda de productos real
    path('producto/', views.buscar_producto, name='buscar_producto'),
    
    # Búsqueda inteligente con sugerencias
    path('producto/sugerencias/', views.buscar_productos_sugerencias, name='buscar_productos_sugerencias'),
    
    # Agregar al carrito real
    path('agregar/', views.agregar_carrito, name='agregar_carrito'),
    
    # ========================
    # API INVENTARIO (USADAS)
    # ========================
    
    # Obtener todos los productos
    path('inventario/api/', views.inventario_api, name='inventario_api'),
    
    # Agregar producto al inventario
    path('inventario/agregar/', views.agregar_producto_inventario, name='agregar_producto_inventario'),
    
    # Actualizar producto en inventario
    path('inventario/actualizar/', views.actualizar_producto_inventario, name='actualizar_producto_inventario'),
    
    # Productos con poco stock (para alertas)
    path('inventario/poco-stock/', views.productos_poco_stock_api, name='productos_poco_stock_api'),
    
    # Obtener producto por ID (para editar)
    path('inventario/producto/<int:producto_id>/', views.obtener_producto_por_id, name='obtener_producto_por_id'),
    
    # Eliminar producto del inventario
    path('inventario/eliminar/<int:producto_id>/', views.eliminar_producto_inventario, name='eliminar_producto_inventario'),
    
    # Obtener stock de producto por código (para verificación post-venta)
    path('inventario/producto/<str:codigo>/stock/', views.obtener_stock_producto, name='obtener_stock_producto'),
    
    # ========================
    # API VENTAS (USADAS)
    # ========================
    
    # Registrar venta completa
    path('punto_de_venta/registrar-venta/', views.registrar_venta, name='registrar_venta'),
    
    # Total de ventas del día
    path('punto_de_venta/total-hoy/', views.total_dia_hoy, name='total_dia_hoy'),
    
    # API para obtener historial de ventas
    path('api/', views.ventas_api, name='ventas_api'),
    
    # ========================
    # CAJA (USADA)
    # ========================
    
    # Control de caja
    path('caja/', views.control_caja, name='control_caja'),
    
    # APIs de caja
    path('caja/api/estado/', views.caja_estado_api, name='caja_estado_api'),
    path('caja/api/abrir/', views.caja_abrir_api, name='caja_abrir_api'),
    path('caja/api/cerrar/', views.caja_cerrar_api, name='caja_cerrar_api'),
    path('caja/api/gastos/', views.caja_gastos_api, name='caja_gastos_api'),
    
    # API de prueba para debugging
    path('caja/api/test/', views.caja_test_api, name='caja_test_api'),
    
    # Setup automático de base de datos
    path('setup-caja-db/', views.setup_caja_db, name='setup_caja_db'),

    # ========================
    # API MOVIMIENTOS DE STOCK (NUEVAS)
    # ========================

    # Registrar movimientos de stock (entradas, salidas, ajustes)
    path('inventario/movimientos/registrar/', views.registrar_movimiento_stock, name='registrar_movimiento_stock'),

    # Obtener historial de movimientos de stock
    path('inventario/movimientos/', views.obtener_movimientos_stock, name='obtener_movimientos_stock'),

    # API específica para frontend de movimientos de stock
    path('inventario/movimientos/api/', views.movimientos_stock_api, name='movimientos_stock_api'),

    # API unificada: registro completo de ventas + movimientos de inventario
    path('registro/completo/', views.registro_completo_api, name='registro_completo_api'),
]