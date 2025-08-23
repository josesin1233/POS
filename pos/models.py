"""
Modelos del sistema POS para Dulcerías México
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid

# Get the User model from accounts app
User = get_user_model()

# Import Business from accounts app instead of redefining it
from accounts.models import Business

# ========================
# MODELOS BASE
# ========================

class Sucursal(models.Model):
    """Modelo para sucursales de un negocio"""
    
    business = models.ForeignKey(
        Business, 
        on_delete=models.CASCADE,
        related_name='sucursales'
    )
    
    nombre = models.CharField(max_length=200, verbose_name="Nombre de la sucursal")
    direccion = models.TextField(blank=True, null=True)
    telefono = models.CharField(max_length=15, blank=True, null=True)
    encargado = models.CharField(max_length=200, blank=True, null=True)
    
    # Configuraciones específicas
    activa = models.BooleanField(default=True)
    es_principal = models.BooleanField(default=False)
    
    # IP permitidas para esta sucursal (seguridad)
    ips_permitidas = models.TextField(
        blank=True, 
        null=True,
        help_text="IPs separadas por comas. Vacío = cualquier IP"
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Sucursal"
        verbose_name_plural = "Sucursales"
        ordering = ['business', 'nombre']
        unique_together = ['business', 'nombre']
    
    def __str__(self):
        return f"{self.business.nombre} - {self.nombre}"



# ========================
# MODELOS DE PRODUCTOS
# ========================

class Categoria(models.Model):
    """Categorías de productos"""
    
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='categorias'
    )
    
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    activa = models.BooleanField(default=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['business', 'nombre']
        unique_together = ['business', 'nombre']
    
    def __str__(self):
        return f"{self.business.nombre} - {self.nombre}"


class Producto(models.Model):
    """Modelo principal de productos"""
    
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='productos'
    )
    
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='productos'
    )
    
    # Información básica del producto
    codigo = models.CharField(max_length=50, verbose_name="Código de barras")
    nombre = models.CharField(max_length=200, verbose_name="Nombre del producto")
    descripcion = models.TextField(blank=True, null=True)
    
    # Precios
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Precio de venta"
    )
    precio_compra = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Precio de compra"
    )
    
    # Inventario
    stock = models.PositiveIntegerField(default=0, verbose_name="Stock actual")
    stock_minimo = models.PositiveIntegerField(
        default=10,
        verbose_name="Stock mínimo"
    )
    stock_maximo = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Stock máximo"
    )
    
    # Configuraciones
    activo = models.BooleanField(default=True)
    requiere_peso = models.BooleanField(default=False)
    permite_decimales = models.BooleanField(default=False)
    
    # Impuestos
    porcentaje_impuesto = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    
    # Metadatos
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='productos_creados'
    )
    
    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['business', 'nombre']
        unique_together = ['business', 'codigo']
        indexes = [
            models.Index(fields=['business', 'codigo']),
            models.Index(fields=['business', 'nombre']),
            models.Index(fields=['business', 'activo']),
        ]
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
    
    def tiene_stock_bajo(self):
        """Verificar si el producto tiene stock bajo"""
        return self.stock < self.stock_minimo
    
    def margen_ganancia(self):
        """Calcular margen de ganancia"""
        if not self.precio_compra:
            return None
        return self.precio - self.precio_compra
    
    def porcentaje_ganancia(self):
        """Calcular porcentaje de ganancia"""
        if not self.precio_compra or self.precio_compra == 0:
            return None
        margen = self.margen_ganancia()
        return (margen / self.precio_compra) * 100
    
    def precio_con_impuesto(self):
        """Precio final con impuestos"""
        impuesto = self.precio * (self.porcentaje_impuesto / 100)
        return self.precio + impuesto


# ========================
# MODELOS DE VENTAS
# ========================

class Venta(models.Model):
    """Modelo principal de ventas"""
    
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
        ('devuelta', 'Devuelta'),
    ]
    
    METODO_PAGO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('tarjeta', 'Tarjeta'),
        ('transferencia', 'Transferencia'),
        ('credito', 'Crédito'),
        ('mixto', 'Mixto'),
    ]
    
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='ventas'
    )
    
    sucursal = models.ForeignKey(
        Sucursal,
        on_delete=models.CASCADE,
        related_name='ventas'
    )
    
    usuario = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='ventas_realizadas'
    )
    
    # Identificación
    folio = models.CharField(max_length=20, unique=True, editable=False)
    
    # Montos
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    impuestos = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    descuento = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Pago
    metodo_pago = models.CharField(
        max_length=20,
        choices=METODO_PAGO_CHOICES,
        default='efectivo'
    )
    monto_pagado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    cambio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Estado y fechas
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='completada'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    # Información adicional
    notas = models.TextField(blank=True, null=True)
    ticket_impreso = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['business', 'fecha_creacion']),
            models.Index(fields=['business', 'estado']),
            models.Index(fields=['sucursal', 'fecha_creacion']),
            models.Index(fields=['usuario', 'fecha_creacion']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.folio:
            self.folio = self.generar_folio()
        super().save(*args, **kwargs)
    
    def generar_folio(self):
        """Generar folio único para la venta"""
        fecha = timezone.now()
        timestamp = fecha.strftime('%Y%m%d%H%M%S')
        ultimo_id = Venta.objects.count() + 1
        return f"V{timestamp}{ultimo_id:04d}"
    
    def __str__(self):
        return f"Venta {self.folio} - ${self.total}"
    
    def calcular_totales(self):
        """Recalcular subtotal, impuestos y total basado en detalles"""
        detalles = self.detalles.all()
        subtotal = sum(detalle.subtotal for detalle in detalles)
        impuestos = sum(detalle.impuestos for detalle in detalles)
        
        self.subtotal = subtotal
        self.impuestos = impuestos
        self.total = subtotal + impuestos - self.descuento
        self.save()


class VentaDetalle(models.Model):
    """Detalle de productos vendidos"""
    
    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name='detalles'
    )
    
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='ventas'
    )
    
    cantidad = models.DecimalField(
        max_digits=8,
        decimal_places=3,
        validators=[MinValueValidator(Decimal('0.001'))]
    )
    
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    descuento_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    impuestos = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    class Meta:
        verbose_name = "Detalle de Venta"
        verbose_name_plural = "Detalles de Venta"
        ordering = ['venta', 'id']
    
    def save(self, *args, **kwargs):
        # Calcular subtotal e impuestos automáticamente
        precio_con_descuento = self.precio_unitario - self.descuento_unitario
        self.subtotal = precio_con_descuento * self.cantidad
        
        # Calcular impuestos basado en el producto
        porcentaje_impuesto = self.producto.porcentaje_impuesto
        self.impuestos = self.subtotal * (porcentaje_impuesto / 100)
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.venta.folio} - {self.producto.nombre} x{self.cantidad}"


# ========================
# MODELOS DE CAJA
# ========================

class Caja(models.Model):
    """Control de caja diario"""
    
    ESTADO_CHOICES = [
        ('abierta', 'Abierta'),
        ('cerrada', 'Cerrada'),
    ]
    
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='cajas'
    )
    
    sucursal = models.ForeignKey(
        Sucursal,
        on_delete=models.CASCADE,
        related_name='cajas'
    )
    
    usuario_apertura = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='cajas_abiertas'
    )
    
    usuario_cierre = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='cajas_cerradas',
        null=True,
        blank=True
    )
    
    # Montos
    monto_inicial = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    monto_final = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    total_ventas = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    total_efectivo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    total_tarjetas = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    diferencia = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Estado y fechas
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='abierta'
    )
    
    fecha_apertura = models.DateTimeField(auto_now_add=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    fecha = models.DateField(auto_now_add=True)
    monto_actual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    efectivo_real = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    hora_cierre = models.DateTimeField(null=True, blank=True)
    
    # Observaciones
    notas_apertura = models.TextField(blank=True, null=True)
    notas_cierre = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Caja"
        verbose_name_plural = "Cajas"
        ordering = ['-fecha_apertura']
        indexes = [
            models.Index(fields=['business', 'fecha_apertura']),
            models.Index(fields=['sucursal', 'estado']),
        ]
    
    def __str__(self):
        fecha = self.fecha_apertura.strftime('%Y-%m-%d')
        return f"Caja {self.sucursal.nombre} - {fecha}"
    
    def calcular_totales(self):
        """Calcular totales basado en ventas del día"""
        ventas = Venta.objects.filter(
            sucursal=self.sucursal,
            fecha_creacion__date=self.fecha_apertura.date(),
            estado='completada'
        )
        
        self.total_ventas = sum(venta.total for venta in ventas)
        self.total_efectivo = sum(
            venta.monto_pagado for venta in ventas 
            if venta.metodo_pago == 'efectivo'
        )
        self.total_tarjetas = sum(
            venta.monto_pagado for venta in ventas 
            if venta.metodo_pago == 'tarjeta'
        )
        
        if self.monto_final is not None:
            esperado = self.monto_inicial + self.total_efectivo
            self.diferencia = self.monto_final - esperado
        
        self.save()


class GastoCaja(models.Model):
    """Gastos y retiros de caja"""
    
    TIPO_CHOICES = [
        ('compra', 'Compra'),
        ('gasto_operativo', 'Gasto Operativo'),
        ('retiro', 'Retiro'),
        ('otro', 'Otro'),
    ]
    
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='gastos_caja'
    )
    
    concepto = models.CharField(max_length=200, verbose_name="Concepto del gasto")
    monto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='otro'
    )
    
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='gastos_realizados'
    )
    
    class Meta:
        verbose_name = "Gasto de Caja"
        verbose_name_plural = "Gastos de Caja"
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['business', 'fecha']),
            models.Index(fields=['business', 'tipo']),
        ]
    
    def __str__(self):
        return f"{self.concepto} - ${self.monto}"


# ========================
# MODELOS DE SUSCRIPCIÓN
# ========================

class Suscripcion(models.Model):
    """Historial de suscripciones y pagos"""
    
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('activa', 'Activa'),
        ('vencida', 'Vencida'),
        ('cancelada', 'Cancelada'),
    ]
    
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='suscripciones'
    )
    
    plan = models.CharField(max_length=20)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente'
    )
    
    # Información de pago
    metodo_pago = models.CharField(max_length=50, blank=True, null=True)
    transaction_id = models.CharField(max_length=200, blank=True, null=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Suscripción"
        verbose_name_plural = "Suscripciones"
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.business.nombre} - {self.plan} ({self.estado})"