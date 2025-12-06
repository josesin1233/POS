from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class Business(models.Model):
    # Basic info
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    max_concurrent_users = models.PositiveIntegerField(default=2)
    subscription_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Extended fields for compatibility with pos models
    plan_actual = models.CharField(max_length=20, default='basico')
    monthly_cost = models.DecimalField(max_digits=8, decimal_places=2, default=299.00)

    @property 
    def is_subscription_active(self):
        """Compatibility property for pos views"""
        return self.subscription_active
    
    def get_plan_display(self):
        """Get display name for plan"""
        plans = {
            'basico': 'Plan Básico',
            'intermedio': 'Plan Intermedio', 
            'profesional': 'Plan Profesional'
        }
        return plans.get(self.plan_actual, 'Plan Básico')

    def __str__(self):
        return self.name


class User(AbstractUser):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    is_business_owner = models.BooleanField(default=False)

    def __str__(self):
        return self.username


class UserSession(models.Model):
    """Modelo para controlar sesiones de usuarios"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-last_activity']

    def __str__(self):
        return f"{self.user.username} - {self.created_at}"


class BusinessSettings(models.Model):
    """Configuraciones específicas del negocio"""
    business = models.OneToOneField(Business, on_delete=models.CASCADE, related_name='settings')
    
    # Configuraciones generales
    currency_symbol = models.CharField(max_length=5, default='$')
    timezone = models.CharField(max_length=50, default='America/Mexico_City')
    
    # Configuraciones de POS
    enable_custom_rounding = models.BooleanField(default=False)
    rounding_precision = models.DecimalField(max_digits=3, decimal_places=2, default=0.50)
    
    # Configuraciones de reportes
    send_daily_reports = models.BooleanField(default=False)
    report_email = models.EmailField(blank=True)
    
    # Configuraciones de inventario
    show_low_stock_alerts = models.BooleanField(default=True)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    
    # Configuraciones de interfaz
    theme = models.CharField(max_length=20, default='light', choices=[
        ('light', 'Claro'),
        ('dark', 'Oscuro'),
    ])
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Configuración de {self.business.name}"


class UserPermissions(models.Model):
    """Permisos específicos para cada usuario del negocio"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='permissions')
    business = models.ForeignKey(Business, on_delete=models.CASCADE)
    
    # Permisos generales
    can_access_pos = models.BooleanField(default=True, verbose_name="Acceso al Punto de Venta")
    can_access_inventory = models.BooleanField(default=True, verbose_name="Acceso al Inventario")
    can_access_reports = models.BooleanField(default=False, verbose_name="Acceso a Reportes")
    can_access_settings = models.BooleanField(default=False, verbose_name="Acceso a Configuración")
    
    # Permisos de inventario
    can_add_products = models.BooleanField(default=True, verbose_name="Agregar Productos")
    can_edit_products = models.BooleanField(default=True, verbose_name="Editar Productos")
    can_delete_products = models.BooleanField(default=False, verbose_name="Eliminar Productos")
    can_adjust_stock = models.BooleanField(default=True, verbose_name="Ajustar Stock")
    
    # Permisos de ventas
    can_process_sales = models.BooleanField(default=True, verbose_name="Procesar Ventas")
    can_apply_discounts = models.BooleanField(default=False, verbose_name="Aplicar Descuentos")
    can_void_sales = models.BooleanField(default=False, verbose_name="Cancelar Ventas")
    can_access_cash_register = models.BooleanField(default=True, verbose_name="Acceso a Caja")
    
    # Permisos administrativos
    can_manage_users = models.BooleanField(default=False, verbose_name="Gestionar Usuarios")
    can_view_financial_reports = models.BooleanField(default=False, verbose_name="Ver Reportes Financieros")
    can_backup_data = models.BooleanField(default=False, verbose_name="Respaldar Datos")
    
    # Límites operacionales
    max_sale_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Monto máximo de venta")
    max_discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="% máximo de descuento")
    
    # Configuraciones de sesión
    session_timeout_minutes = models.PositiveIntegerField(default=480, verbose_name="Timeout de sesión (minutos)")
    require_pin_for_sensitive = models.BooleanField(default=False, verbose_name="Requiere PIN para operaciones sensibles")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['user', 'business']]
        verbose_name = "Permisos de Usuario"
        verbose_name_plural = "Permisos de Usuarios"

    def __str__(self):
        return f"Permisos de {self.user.username} en {self.business.name}"
    
    @classmethod
    def create_default_permissions(cls, user, business, is_owner=False):
        """Crear permisos por defecto para un usuario"""
        if is_owner:
            # Permisos completos para el propietario
            permissions = cls.objects.create(
                user=user,
                business=business,
                can_access_pos=True,
                can_access_inventory=True,
                can_access_reports=True,
                can_access_settings=True,
                can_add_products=True,
                can_edit_products=True,
                can_delete_products=True,
                can_adjust_stock=True,
                can_process_sales=True,
                can_apply_discounts=True,
                can_void_sales=True,
                can_access_cash_register=True,
                can_manage_users=True,
                can_view_financial_reports=True,
                can_backup_data=True,
                max_discount_percent=100,
                session_timeout_minutes=720  # 12 horas
            )
        else:
            # Permisos básicos para empleados
            permissions = cls.objects.create(
                user=user,
                business=business,
                can_access_pos=True,
                can_access_inventory=True,
                can_access_reports=False,
                can_access_settings=False,
                can_add_products=True,
                can_edit_products=True,
                can_delete_products=False,
                can_adjust_stock=True,
                can_process_sales=True,
                can_apply_discounts=False,
                can_void_sales=False,
                can_access_cash_register=True,
                can_manage_users=False,
                can_view_financial_reports=False,
                can_backup_data=False,
                max_sale_amount=10000,  # $10,000 límite
                max_discount_percent=5,
                session_timeout_minutes=480  # 8 horas
            )
        return permissions