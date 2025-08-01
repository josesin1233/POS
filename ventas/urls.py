 
from django.urls import path
from . import views

app_name = 'ventas'

urlpatterns = [
    path('', views.ventas_view, name='ventas'),
    path('api/', views.VentasAPIView.as_view(), name='ventas_api'),
    path('api/estadisticas/', views.EstadisticasVentasView.as_view(), name='estadisticas'),
    path('api/reporte-diario/', views.ReporteDiarioView.as_view(), name='reporte_diario'),
    path('api/exportar/', views.ExportarVentasView.as_view(), name='exportar_ventas'),
    path('api/resumen-diario/', views.ResumenDiarioAPIView.as_view(), name='resumen_diario'),
]