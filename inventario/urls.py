from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    path('', views.inventario_view, name='inventario'),
    path('agregar/', views.agregar_producto, name='agregar_producto'),
    path('agregar', views.agregar_producto, name='agregar_producto_no_slash'),
    path('api/', views.inventario_api, name='inventario_api'),
    path('api', views.inventario_api, name='inventario_api_no_slash'),
    path('poco-stock/', views.poco_stock_api, name='poco_stock'),
    path('poco-stock', views.poco_stock_api, name='poco_stock_no_slash'),
    path('actualizar/', views.actualizar_producto, name='actualizar_producto'),
]