"""
Modelos para gestión de usuarios y proceso de suscripción
"""
import uuid
from django.db import models
from django.utils import timezone
from datetime import timedelta
from accounts.models import User, Business


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
        self.token_expires_at = timezone.now() + timedelta(hours=72)
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