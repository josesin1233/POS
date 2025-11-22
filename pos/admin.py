from django.contrib import admin
from .models import Producto, Venta, VentaDetalle, Categoria, Sucursal, MovimientoStock
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone

# Configurar el admin site
admin.site.site_header = "Administración POS México"
admin.site.site_title = "POS México"
admin.site.index_title = "Panel de Administración"

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'business', 'activa', 'fecha_creacion', 'productos_count']
    list_filter = ['activa', 'business', 'fecha_creacion']
    search_fields = ['nombre', 'descripcion']
    list_editable = ['activa']
    ordering = ['business', 'nombre']
    
    def productos_count(self, obj):
        count = obj.productos.count()
        return format_html('<span style="color: green; font-weight: bold;">{}</span>', count)
    productos_count.short_description = "Productos"

@admin.register(Sucursal)
class SucursalAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'business', 'activa', 'es_principal', 'encargado', 'fecha_creacion']
    list_filter = ['activa', 'es_principal', 'business', 'fecha_creacion']
    search_fields = ['nombre', 'direccion', 'encargado']
    list_editable = ['activa', 'es_principal']
    ordering = ['business', 'nombre']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('business', 'nombre', 'activa', 'es_principal')
        }),
        ('Detalles', {
            'fields': ('direccion', 'telefono', 'encargado')
        }),
        ('Configuración Técnica', {
            'fields': ('ips_permitidas',),
            'classes': ('collapse',)
        }),
    )

@admin.register(Producto) 
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'categoria', 'precio_formatted', 'stock_display', 'business', 'activo']
    list_filter = ['activo', 'categoria', 'business', 'fecha_creacion']
    search_fields = ['codigo', 'nombre', 'descripcion']
    list_editable = ['activo']
    ordering = ['business', 'nombre']
    list_per_page = 50
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('business', 'codigo', 'nombre', 'categoria', 'descripcion', 'activo')
        }),
        ('Precios', {
            'fields': ('precio', 'precio_compra', 'porcentaje_impuesto')
        }),
        ('Inventario', {
            'fields': ('stock', 'stock_minimo', 'stock_maximo')
        }),
        ('Configuración', {
            'fields': ('requiere_peso', 'permite_decimales'),
            'classes': ('collapse',)
        }),
    )
    
    def precio_formatted(self, obj):
        return format_html('<span style="color: green; font-weight: bold;">${:,.2f}</span>', obj.precio)
    precio_formatted.short_description = "Precio de Venta"
    
    def stock_display(self, obj):
        if obj.stock <= obj.stock_minimo:
            color = 'red'
        elif obj.stock <= obj.stock_minimo * 2:
            color = 'orange'
        else:
            color = 'green'
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.stock)
    stock_display.short_description = "Stock Actual"

@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ['id', 'fecha_creacion', 'business', 'usuario', 'total_formatted', 'productos_count']
    list_filter = ['fecha_creacion', 'business', 'usuario']
    search_fields = ['id', 'usuario__username', 'usuario__email']
    date_hierarchy = 'fecha_creacion'
    ordering = ['-fecha_creacion']
    readonly_fields = ['fecha_creacion']
    list_per_page = 25
    
    def total_formatted(self, obj):
        return format_html('<span style="color: green; font-weight: bold;">${:,.2f}</span>', obj.total)
    total_formatted.short_description = "Total"
    
    def productos_count(self, obj):
        count = obj.detalles.count()
        return format_html('<span style="color: blue;">{} productos</span>', count)
    productos_count.short_description = "Items"

@admin.register(VentaDetalle)
class VentaDetalleAdmin(admin.ModelAdmin):
    list_display = ['venta_id', 'producto', 'cantidad', 'precio_unitario_formatted', 'subtotal_formatted', 'fecha']
    list_filter = ['venta__fecha_creacion', 'producto__business']
    search_fields = ['producto__nombre', 'producto__codigo', 'venta__id']
    date_hierarchy = 'venta__fecha_creacion'
    ordering = ['-venta__fecha_creacion']
    list_per_page = 50
    
    def venta_id(self, obj):
        return obj.venta.id
    venta_id.short_description = "Venta ID"
    
    def fecha(self, obj):
        return obj.venta.fecha_creacion.strftime("%Y-%m-%d %H:%M")
    fecha.short_description = "Fecha"
    
    def precio_unitario_formatted(self, obj):
        return format_html('<span style="color: blue;">${:,.2f}</span>', obj.precio_unitario)
    precio_unitario_formatted.short_description = "Precio Unit."
    
    def subtotal_formatted(self, obj):
        return format_html('<span style="color: green; font-weight: bold;">${:,.2f}</span>', obj.subtotal)
    subtotal_formatted.short_description = "Subtotal"


@admin.register(MovimientoStock)
class MovimientoStockAdmin(admin.ModelAdmin):
    list_display = [
        'fecha_movimiento', 'business', 'producto_info', 'tipo_movimiento',
        'cantidad_display', 'stock_anterior', 'stock_nuevo', 'usuario', 'motivo_corto'
    ]
    list_filter = [
        'tipo_movimiento', 'business', 'fecha_movimiento', 'usuario'
    ]
    search_fields = [
        'producto__codigo', 'producto__nombre', 'motivo', 'venta__folio', 'usuario__username'
    ]
    date_hierarchy = 'fecha_movimiento'
    ordering = ['-fecha_movimiento']
    readonly_fields = [
        'fecha_movimiento', 'stock_anterior', 'stock_nuevo', 'ip_address'
    ]
    list_per_page = 50

    fieldsets = (
        ('Información del Movimiento', {
            'fields': ('business', 'producto', 'tipo_movimiento', 'cantidad')
        }),
        ('Stock', {
            'fields': ('stock_anterior', 'stock_nuevo')
        }),
        ('Referencias', {
            'fields': ('venta', 'usuario', 'motivo')
        }),
        ('Información Técnica', {
            'fields': ('fecha_movimiento', 'ip_address'),
            'classes': ('collapse',)
        }),
    )

    def producto_info(self, obj):
        return format_html(
            '<strong>{}</strong><br><small style="color: gray;">{}</small>',
            obj.producto.nombre,
            obj.producto.codigo
        )
    producto_info.short_description = "Producto"

    def cantidad_display(self, obj):
        if obj.cantidad > 0:
            color = 'green'
            signo = '+'
        else:
            color = 'red'
            signo = ''
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}{}</span>',
            color, signo, obj.cantidad
        )
    cantidad_display.short_description = "Cantidad"

    def motivo_corto(self, obj):
        if len(obj.motivo or '') > 40:
            return (obj.motivo or '')[:37] + '...'
        return obj.motivo or '-'
    motivo_corto.short_description = "Motivo"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'business', 'producto', 'usuario', 'venta'
        )


# ====================================
# ADMIN PARA GESTIÓN DE USUARIOS
# ====================================

# Registrar los modelos de gestión de usuarios directamente aquí
from .models import UserRegistration, UserRegistrationLog

@admin.register(UserRegistration)
class UserRegistrationAdmin(admin.ModelAdmin):
    """
    Admin súper personalizado para gestión visual de usuarios
    """

    # Lista principal
    list_display = [
        'registration_id_display',
        'full_name',
        'email',
        'phone',
        'city',
        'status_timeline',
        'created_at_formatted',
        'action_buttons',
    ]

    list_filter = [
        'status',
        'created_at',
        'source',
    ]

    search_fields = [
        'full_name',
        'email',
        'phone',
        'pk',
    ]

    readonly_fields = [
        'created_at',
        'registration_token',
        'token_expires_at',
        'token_used_at',
        'pos_user',
        'business',
        'timeline_visual',
        'registration_url_display',
    ]

    fieldsets = [
        ('Información básica', {
            'fields': (
                'full_name',
                'email',
                'phone',
                'city',
                'source',
            )
        }),
        ('Estado y progreso', {
            'fields': (
                'status',
                'timeline_visual',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'mensaje_enviado_at',
                'contactado_at',
                'pago_pendiente_at',
                'pago_completado_at',
                'link_enviado_at',
                'registro_completo_at',
            ),
            'classes': ('collapse',)
        }),
        ('Sistema de registro', {
            'fields': (
                'registration_token',
                'registration_url_display',
                'token_expires_at',
                'token_used',
                'token_used_at',
            ),
            'classes': ('collapse',)
        }),
        ('Usuario final', {
            'fields': (
                'pos_user',
                'business',
            ),
            'classes': ('collapse',)
        }),
        ('Notas', {
            'fields': (
                'notes',
            )
        }),
    ]

    # Ordenar por fecha
    ordering = ['-created_at']

    class Media:
        css = {
            'all': ('admin/css/user_management.css',)
        }
        js = ('admin/js/user_management.js',)

    def registration_id_display(self, obj):
        """Muestra ID con formato bonito"""
        return format_html(
            '<span class="registration-id">#{}</span>',
            obj.pk
        )
    registration_id_display.short_description = 'ID'

    def status_timeline(self, obj):
        """Línea de tiempo visual del estado"""
        # Estados y sus íconos
        statuses = [
            ('nuevo', '👤', 'Nuevo'),
            ('mensaje_enviado', '📱', 'Mensaje'),
            ('contactado', '💬', 'Contactado'),
            ('pago_pendiente', '⏳', 'Pago Pdte'),
            ('pago_completado', '💰', 'Pagado'),
            ('link_enviado', '🔗', 'Link'),
            ('registro_completo', '✅', 'Completo'),
            ('activo', '🚀', 'Activo'),
        ]

        timeline_html = '<div class="timeline-container">'

        for i, (status_key, icon, label) in enumerate(statuses):
            # Determinar si este estado está completado
            is_current = (obj.status == status_key)
            is_completed = (i <= self._get_status_index(obj.status, [s[0] for s in statuses]))

            # Clase CSS según el estado
            if is_current:
                css_class = "timeline-step current"
            elif is_completed:
                css_class = "timeline-step completed"
            else:
                css_class = "timeline-step pending"

            timeline_html += f'''
            <div class="{css_class}" title="{label}">
                <div class="timeline-icon">{icon}</div>
                <div class="timeline-label">{label}</div>
            </div>
            '''

            # Línea conectora (excepto el último)
            if i < len(statuses) - 1:
                line_class = "timeline-line completed" if is_completed else "timeline-line pending"
                timeline_html += f'<div class="{line_class}"></div>'

        timeline_html += '</div>'

        return format_html(timeline_html)

    status_timeline.short_description = 'Progreso'

    def _get_status_index(self, status, status_list):
        """Helper para obtener índice del estado"""
        try:
            return status_list.index(status)
        except ValueError:
            return -1

    def created_at_formatted(self, obj):
        """Fecha formateada bonita"""
        return obj.created_at.strftime('%d/%m/%Y %H:%M')
    created_at_formatted.short_description = 'Fecha registro'

    def action_buttons(self, obj):
        """Botones de acción según el estado"""
        buttons_html = ''

        next_status = obj.get_next_status()

        if next_status:
            # Botón para avanzar al siguiente estado
            action_labels = {
                'mensaje_enviado': '📱 Marcar mensaje enviado',
                'contactado': '💬 Marcar como contactado',
                'pago_pendiente': '⏳ Marcar pago pendiente',
                'pago_completado': '💰 Confirmar pago',
                'link_enviado': '🔗 Generar y enviar link',
                'registro_completo': '✅ Marcar completo',
                'activo': '🚀 Activar usuario',
            }

            button_label = action_labels.get(next_status, f'Avanzar a {next_status}')

            buttons_html += f'''
            <a href="/admin/pos/userregistration/{obj.pk}/advance/"
               class="button advance-btn"
               title="{button_label}">
               {button_label}
            </a>
            '''

        # Botón de ver detalles siempre presente
        buttons_html += f'''
        <a href="/admin/pos/userregistration/{obj.pk}/change/"
           class="button view-btn"
           title="Ver detalles">
           👁️ Ver
        </a>
        '''

        # Botón especial si hay link de registro
        if obj.registration_token and obj.is_token_valid():
            buttons_html += f'''
            <a href="/admin/pos/userregistration/{obj.pk}/copy-link/"
               class="button link-btn"
               title="Copiar link de registro">
               📋 Copiar Link
            </a>
            '''

        return format_html(
            '<div class="action-buttons">{}</div>',
            buttons_html
        )

    action_buttons.short_description = 'Acciones'

    def timeline_visual(self, obj):
        """Timeline visual más detallado para la vista individual"""
        return self.status_timeline(obj)
    timeline_visual.short_description = 'Línea de tiempo'

    def registration_url_display(self, obj):
        """Muestra la URL de registro si existe"""
        if obj.registration_token:
            url = f"/registro/complete/{obj.registration_token}/"
            return format_html(
                '<a href="{}" target="_blank" class="registration-link">{}</a>',
                url,
                url
            )
        return "No generado"
    registration_url_display.short_description = 'URL de registro'

    def get_urls(self):
        """Agregar URLs personalizadas para acciones del admin"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:registration_id>/advance/',
                self.admin_site.admin_view(self.advance_status_view),
                name='userregistration-advance',
            ),
            path(
                '<int:registration_id>/copy-link/',
                self.admin_site.admin_view(self.copy_link_view),
                name='userregistration-copy-link',
            ),
        ]
        return custom_urls + urls

    def advance_status_view(self, request, registration_id):
        """Vista para avanzar al siguiente estado"""
        registration = get_object_or_404(UserRegistration, pk=registration_id)

        # Guardar estado anterior para el mensaje
        previous_status = registration.get_status_display()

        # Intentar avanzar al siguiente estado
        success = registration.advance_status()

        if success:
            # Crear log de la acción
            UserRegistrationLog.objects.create(
                registration=registration,
                action='status_change',
                description=f'Estado cambiado de "{previous_status}" a "{registration.get_status_display()}"',
                created_by=request.user
            )

            messages.success(
                request,
                f'Estado actualizado a: {registration.get_status_display()}'
            )
        else:
            messages.warning(
                request,
                'No hay siguiente estado disponible'
            )

        # Redirigir de vuelta a la lista o a la página de detalle
        if request.GET.get('next') == 'detail':
            return redirect('admin:pos_userregistration_change', registration_id)
        return redirect('admin:pos_userregistration_changelist')

    def copy_link_view(self, request, registration_id):
        """Vista para obtener el link de registro (para copiar)"""
        registration = get_object_or_404(UserRegistration, pk=registration_id)

        # Verificar si tiene token
        if not registration.registration_token:
            return JsonResponse({
                'error': 'Este registro no tiene un token generado aún'
            }, status=400)

        # Verificar si el token es válido
        if not registration.is_token_valid():
            return JsonResponse({
                'error': 'El token ha expirado o ya fue usado'
            }, status=400)

        # Construir URL completa
        registration_url = registration.get_registration_url()

        # En producción, incluir el dominio completo
        if request.is_secure():
            protocol = 'https'
        else:
            protocol = 'http'

        full_url = f"{protocol}://{request.get_host()}{registration_url}"

        # Crear log de la acción
        UserRegistrationLog.objects.create(
            registration=registration,
            action='link_copied',
            description=f'Link de registro copiado por {request.user.username}',
            created_by=request.user
        )

        return JsonResponse({
            'url': full_url,
            'expires_at': registration.token_expires_at.isoformat() if registration.token_expires_at else None,
            'token': str(registration.registration_token)
        })


@admin.register(UserRegistrationLog)
class UserRegistrationLogAdmin(admin.ModelAdmin):
    """Admin para logs de acciones"""

    list_display = [
        'registration',
        'action',
        'description',
        'created_by',
        'created_at',
    ]

    list_filter = [
        'action',
        'created_at',
    ]

    search_fields = [
        'registration__full_name',
        'registration__email',
        'action',
        'description',
    ]

    readonly_fields = [
        'registration',
        'action',
        'description',
        'created_at',
        'created_by',
    ]


# ====================================
# DASHBOARD PERSONALIZADO
# ====================================

from django.contrib.admin import AdminSite as BaseAdminSite
from django.db.models import F

class CustomAdminSite(BaseAdminSite):
    site_header = "POS México - Panel Ejecutivo"
    site_title = "POS México"
    index_title = "Dashboard"

    def index(self, request, extra_context=None):
        """Dashboard personalizado con estadísticas"""
        from .models import UserRegistration, Venta, Producto
        from django.db.models import Sum, Count
        from datetime import timedelta
        
        # Estadísticas de usuarios
        total_usuarios = UserRegistration.objects.count()
        usuarios_nuevos = UserRegistration.objects.filter(status='nuevo').count()
        usuarios_pago = UserRegistration.objects.filter(
            status__in=['pago_pendiente', 'pago_completado']
        ).count()
        usuarios_activos = UserRegistration.objects.filter(status='activo').count()
        
        # Últimos 5 registros
        ultimos_usuarios = UserRegistration.objects.order_by('-created_at')[:5]
        
        context = {
            **self.each_context(request),
            'total_usuarios': total_usuarios,
            'usuarios_nuevos': usuarios_nuevos,
            'usuarios_pago': usuarios_pago,
            'usuarios_activos': usuarios_activos,
            'ultimos_usuarios': ultimos_usuarios,
        }
        
        if extra_context:
            context.update(extra_context)
            
        # Usar el template personalizado
        request.current_app = self.name
        return render(request, 'admin/index.html', context)

# Reemplazar el admin site por defecto
from django.contrib import admin as django_admin
admin_site = CustomAdminSite(name='admin')

# Re-registrar todos los modelos en el nuevo admin site
admin_site.register(Categoria, CategoriaAdmin)
admin_site.register(Sucursal, SucursalAdmin)
admin_site.register(Producto, ProductoAdmin)
admin_site.register(Venta, VentaAdmin)
admin_site.register(VentaDetalle, VentaDetalleAdmin)
admin_site.register(MovimientoStock, MovimientoStockAdmin)
admin_site.register(UserRegistration, UserRegistrationAdmin)
admin_site.register(UserRegistrationLog, UserRegistrationLogAdmin)

# Importante: reemplazar django.admin.site con nuestro site personalizado
django_admin.site = admin_site
