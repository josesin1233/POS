from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class Business(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)  # Campo que agregamos antes
    max_concurrent_users = models.PositiveIntegerField(default=2)
    subscription_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, null=True, blank=True)
    phone = models.CharField(max_length=15, blank=True)
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