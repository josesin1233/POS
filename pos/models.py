from django.db import models
from django.utils import timezone
from decimal import Decimal
from accounts.models import Business, User

class Producto(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='productos')
    codigo = models.CharField('Código', max_length=50)
    nombre = models.CharField('Nombre', max_length=200)
    precio = models.DecimalField('Precio', max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField('Stock', default=0)
    stock_minimo = models.PositiveIntegerField('Stock mínimo', default=0)
    categoria = models.CharField('Categoría', max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        unique_together = [['business', 'codigo']]
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
    
    @property
    def tiene_stock_bajo(self):
        return self.stock <= self.stock_minimo and self.stock_minimo > 0

class Venta(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='ventas')
    vendedor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    total_venta = models.DecimalField('Total', max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)
    monto_pagado = models.DecimalField('Monto pagado', max_digits=10, decimal_places=2, default=0)
    cambio = models.DecimalField('Cambio', max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        ordering = ['-fecha']
    
    def __str__(self):
        return f"Venta #{self.id} - ${self.total_venta}"

class VentaDetalle(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='productos')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    codigo_producto = models.CharField(max_length=50)
    nombre_producto = models.CharField(max_length=200)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_vendida = models.PositiveIntegerField()
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.nombre_producto} x{self.cantidad_vendida}"

# AGREGAR ESTE MODELO AL FINAL:
class ResumenDiario(models.Model):
    """Resumen de ventas diarias"""
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='resumenes_diarios')
    fecha = models.DateField('Fecha')
    total_ventas = models.DecimalField('Total ventas', max_digits=10, decimal_places=2, default=0)
    cantidad_ventas = models.PositiveIntegerField('Cantidad de ventas', default=0)
    productos_vendidos = models.PositiveIntegerField('Productos vendidos', default=0)
    vendedor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Información adicional
    efectivo_recibido = models.DecimalField('Efectivo recibido', max_digits=10, decimal_places=2, default=0)
    cambio_entregado = models.DecimalField('Cambio entregado', max_digits=10, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['business', 'fecha']]
        ordering = ['-fecha']
    
    def __str__(self):
        return f"Resumen {self.fecha} - ${self.total_ventas}"