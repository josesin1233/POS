from django.urls import path
from . import views

app_name = 'pos'

urlpatterns = [
    path('', views.index, name='index'),
    
    # APIs del POS - AGREGAR ESTAS LÍNEAS
    path('producto/', views.ProductoAPIView.as_view(), name='producto_api'),
    path('producto', views.ProductoAPIView.as_view(), name='producto_api_no_slash'),
    path('agregar/', views.AgregarProductoView.as_view(), name='agregar_producto'),  
    path('agregar', views.AgregarProductoView.as_view(), name='agregar_producto_no_slash'),
]