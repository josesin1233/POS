from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from pos.views import index_view, buscar_producto, agregar_carrito, ventas_api, caja_estado_api, caja_abrir_api, caja_cerrar_api, caja_gastos_api
from django.shortcuts import render
import os

def registro_view(request):
    return render(request, 'registro.html')

def caja_view(request):
    return render(request, 'caja.html')

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Landing page as homepage
    path('', index_view, name='home'),
    
    # Registro template
    path('registro/', registro_view, name='registro'),
    
    # Caja template
    path('caja/', caja_view, name='caja'),
    
    # Global API endpoints (used by templates)
    path('producto/', buscar_producto, name='buscar_producto_global'),
    path('agregar/', agregar_carrito, name='agregar_carrito_global'),
    
    # Ventas API directo para registro template
    path('ventas/api/', ventas_api, name='ventas_api_global'),
    
    # Caja APIs
    path('caja/api/estado/', caja_estado_api, name='caja_estado_api'),
    path('caja/api/abrir/', caja_abrir_api, name='caja_abrir_api'),
    path('caja/api/cerrar/', caja_cerrar_api, name='caja_cerrar_api'),
    path('caja/api/gastos/', caja_gastos_api, name='caja_gastos_api'),
    
    # Apps principales  
    path('', include('pos.urls')),               # Include POS URLs at root level
    path('accounts/', include('accounts.urls')),
]

# Servir archivos estáticos en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=os.path.join(settings.BASE_DIR, 'static'))
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)