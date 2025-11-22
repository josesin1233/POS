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
# MODELOS DE INVENTARIO
# ========================

class MovimientoStock(models.Model):
    """Registro de todos los movimientos de inventario"""

    TIPO_MOVIMIENTO_CHOICES = [
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
        ('ajuste', 'Ajuste'),
        ('venta', 'Venta'),
        ('compra', 'Compra'),
        ('devolucion', 'Devolución'),
        ('merma', 'Merma'),
    ]

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='movimientos_stock'
    )

    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='movimientos'
    )

    tipo_movimiento = models.CharField(
        max_length=20,
        choices=TIPO_MOVIMIENTO_CHOICES
    )

    cantidad = models.IntegerField(
        help_text="Cantidad de productos (positivo para entradas, negativo para salidas)"
    )

    stock_anterior = models.PositiveIntegerField(
        verbose_name="Stock antes del movimiento"
    )

    stock_nuevo = models.PositiveIntegerField(
        verbose_name="Stock después del movimiento"
    )

    # Referencias opcionales a otros modelos
    venta = models.ForeignKey(
        'Venta',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='movimientos_stock'
    )

    usuario = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='movimientos_stock_realizados'
    )

    motivo = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Descripción del movimiento"
    )

    fecha_movimiento = models.DateTimeField(auto_now_add=True)

    # Información adicional para trazabilidad
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP desde donde se hizo el movimiento"
    )

    class Meta:
        verbose_name = "Movimiento de Stock"
        verbose_name_plural = "Movimientos de Stock"
        ordering = ['-fecha_movimiento']
        indexes = [
            models.Index(fields=['business', 'fecha_movimiento']),
            models.Index(fields=['producto', 'fecha_movimiento']),
            models.Index(fields=['business', 'tipo_movimiento']),
            models.Index(fields=['venta']),
        ]

    def __str__(self):
        signo = '+' if self.cantidad > 0 else ''
        return f"{self.producto.nombre} - {signo}{self.cantidad} ({self.get_tipo_movimiento_display()})"

    def save(self, *args, **kwargs):
        # Validar que el stock nuevo sea consistente
        if self.stock_anterior + self.cantidad != self.stock_nuevo:
            raise ValueError(
                f"Inconsistencia en stock: {self.stock_anterior} + {self.cantidad} ≠ {self.stock_nuevo}"
            )
        super().save(*args, **kwargs)


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


class SubscriptionPlan(models.Model):
    """Planes de suscripción disponibles"""

    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    # Configuraciones del plan
    max_concurrent_users = models.IntegerField(default=2)
    duration_days = models.IntegerField(default=30)

    # Jerarquía de planes
    hierarchy_level = models.IntegerField(default=1)  # 1=básico, 2=intermedio, 3=avanzado

    # Estado
    is_active = models.BooleanField(default=True)
    is_promotional = models.BooleanField(default=False)
    promotional_text = models.CharField(max_length=100, blank=True)

    # Metadatos
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Plan de Suscripción"
        verbose_name_plural = "Planes de Suscripción"
        ordering = ['hierarchy_level', 'price']

    def __str__(self):
        return f"{self.display_name} (${self.price})"


class PlanFeature(models.Model):
    """Características/funcionalidades de cada plan"""

    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.CASCADE,
        related_name='features'
    )

    name = models.CharField(max_length=100)
    description = models.TextField()
    feature_key = models.CharField(max_length=50)  # Para verificar en código

    # Orden de aparición
    display_order = models.IntegerField(default=1)

    class Meta:
        verbose_name = "Característica del Plan"
        verbose_name_plural = "Características del Plan"
        ordering = ['display_order']

    def __str__(self):
        return f"{self.plan.name} - {self.name}"


class PaymentTransaction(models.Model):
    """Transacciones de pago"""

    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('processing', 'Procesando'),
        ('completed', 'Completado'),
        ('failed', 'Fallido'),
        ('refunded', 'Reembolsado'),
        ('cancelled', 'Cancelado'),
    ]

    GATEWAY_CHOICES = [
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('mercadopago', 'Mercado Pago'),
        ('manual', 'Manual'),
    ]

    # Identificadores
    transaction_id = models.CharField(max_length=200, unique=True)
    gateway_transaction_id = models.CharField(max_length=200, blank=True, null=True)

    # Relaciones
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='payment_transactions'
    )
    subscription = models.ForeignKey(
        'Suscripcion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payment_transactions'
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Datos de pago
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='MXN')
    gateway = models.CharField(max_length=20, choices=GATEWAY_CHOICES)
    payment_method = models.CharField(max_length=50, blank=True)

    # Estados
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Datos del gateway
    gateway_response = models.JSONField(blank=True, null=True)

    # Fechas
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Transacción de Pago"
        verbose_name_plural = "Transacciones de Pago"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_id} - {self.business.name} (${self.amount})"


class SubscriptionRegistration(models.Model):
    """Registro temporal antes de completar pago"""

    # Datos del formulario de registro
    business_name = models.CharField(max_length=100)
    business_type = models.CharField(max_length=50)
    address = models.TextField()
    state = models.CharField(max_length=50)
    country = models.CharField(max_length=50, default='México')

    # Datos de contacto
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=15)

    # Datos del usuario administrador
    admin_username = models.CharField(max_length=150)
    admin_password = models.CharField(max_length=200)  # Hash de la contraseña
    admin_first_name = models.CharField(max_length=150)
    admin_last_name = models.CharField(max_length=150)

    # Plan seleccionado
    selected_plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.CASCADE
    )

    # Estado del registro
    is_completed = models.BooleanField(default=False)
    payment_transaction = models.ForeignKey(
        PaymentTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Fechas
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Registro de Suscripción"
        verbose_name_plural = "Registros de Suscripción"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.business_name} - {self.selected_plan.name}"


# ====================================
# MODELOS DE GESTIÓN DE USUARIOS
# ====================================

class UserRegistration(models.Model):
    """
    Modelo para tracking completo del proceso de registro/suscripción
    """

    # Estados del proceso
    STATUS_CHOICES = [
        ('nuevo', '🆕 Nuevo Lead'),
        ('mensaje_enviado', '📱 Mensaje Enviado'),
        ('contactado', '💬 Contactado'),
        ('pago_pendiente', '⏳ Pago Pendiente'),
        ('pago_completado', '💰 Pago Completado'),
        ('link_enviado', '🔗 Link Enviado'),
        ('registro_completo', '✅ Registro Completo'),
        ('activo', '🚀 Usuario Activo'),
        ('vencido', '⚠️ Suscripción Vencida'),
        ('cancelado', '❌ Cancelado'),
    ]

    # Información básica del formulario
    full_name = models.CharField(
        max_length=100,
        verbose_name="Nombre completo"
    )
    email = models.EmailField(
        verbose_name="Email",
        unique=True
    )
    phone = models.CharField(
        max_length=20,
        verbose_name="Teléfono"
    )
    city = models.CharField(
        max_length=50,
        verbose_name="Ciudad"
    )

    # Control del proceso
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='nuevo',
        verbose_name="Estado"
    )

    # Timestamps del proceso
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de registro"
    )
    mensaje_enviado_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Mensaje enviado"
    )
    contactado_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Contactado"
    )
    pago_pendiente_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Pago pendiente desde"
    )
    pago_completado_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Pago completado"
    )
    link_enviado_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Link enviado"
    )
    registro_completo_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Registro completado"
    )

    # Sistema de links únicos
    registration_token = models.UUIDField(
        unique=True,
        null=True, blank=True,
        verbose_name="Token de registro"
    )
    token_expires_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Token expira"
    )
    token_used = models.BooleanField(
        default=False,
        verbose_name="Token usado"
    )
    token_used_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Token usado en"
    )

    # Relación con usuario final
    pos_user = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Usuario POS"
    )
    business = models.OneToOneField(
        Business,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Negocio"
    )

    # Metadata adicional
    notes = models.TextField(
        blank=True,
        verbose_name="Notas administrativas"
    )
    source = models.CharField(
        max_length=50,
        default='formulario_web',
        verbose_name="Origen"
    )

    class Meta:
        verbose_name = "Registro de Usuario"
        verbose_name_plural = "Gestión de Usuarios"
        ordering = ['-created_at']

    def __str__(self):
        return f"#{self.pk} - {self.full_name} ({self.get_status_display()})"

    @property
    def registration_id(self):
        """ID único para mostrar al usuario"""
        return f"REG{self.pk:04d}"

    def get_timeline_progress(self):
        """Devuelve el progreso en la línea de tiempo (0-100%)"""
        status_order = [
            'nuevo', 'mensaje_enviado', 'contactado',
            'pago_pendiente', 'pago_completado', 'link_enviado',
            'registro_completo', 'activo'
        ]
        try:
            current_index = status_order.index(self.status)
            return int((current_index / (len(status_order) - 1)) * 100)
        except ValueError:
            return 0

    def get_next_status(self):
        """Obtiene el siguiente estado lógico"""
        status_flow = {
            'nuevo': 'mensaje_enviado',
            'mensaje_enviado': 'contactado',
            'contactado': 'pago_pendiente',
            'pago_pendiente': 'pago_completado',
            'pago_completado': 'link_enviado',
            'link_enviado': 'registro_completo',
            'registro_completo': 'activo',
        }
        return status_flow.get(self.status)

    def advance_status(self, new_status=None, save=True):
        """Avanza al siguiente estado y actualiza timestamp"""
        if new_status is None:
            new_status = self.get_next_status()

        if new_status is None:
            return False

        # Actualizar timestamp correspondiente
        now = timezone.now()
        timestamp_fields = {
            'mensaje_enviado': 'mensaje_enviado_at',
            'contactado': 'contactado_at',
            'pago_pendiente': 'pago_pendiente_at',
            'pago_completado': 'pago_completado_at',
            'link_enviado': 'link_enviado_at',
            'registro_completo': 'registro_completo_at',
        }

        self.status = new_status

        if new_status in timestamp_fields:
            setattr(self, timestamp_fields[new_status], now)

        # Lógica especial para ciertos estados
        if new_status == 'pago_completado':
            self.generate_registration_token()

        if save:
            self.save()

        return True

    def generate_registration_token(self):
        """Genera token único para registro"""
        self.registration_token = uuid.uuid4()
        self.token_expires_at = timezone.now() + timezone.timedelta(hours=72)
        self.token_used = False

    def get_registration_url(self):
        """Obtiene la URL de registro única"""
        if self.registration_token:
            return f"/registro/complete/{self.registration_token}/"
        return None

    def use_token(self):
        """Marca el token como usado"""
        self.token_used = True
        self.token_used_at = timezone.now()
        self.advance_status('registro_completo')

    def is_token_valid(self):
        """Verifica si el token es válido"""
        if not self.registration_token:
            return False
        if self.token_used:
            return False
        if self.token_expires_at and timezone.now() > self.token_expires_at:
            return False
        return True


class UserRegistrationLog(models.Model):
    """
    Log de acciones realizadas en el proceso de registro
    """
    registration = models.ForeignKey(
        UserRegistration,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    action = models.CharField(max_length=50)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.registration.full_name} - {self.action}"