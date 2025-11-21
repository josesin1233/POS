"""
Admin personalizado para gestión de usuarios con línea de tiempo visual
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Q
from .models_user_management import UserRegistration, UserRegistrationLog


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

    # Acciones personalizadas
    actions = [
        'mark_as_mensaje_enviado',
        'mark_as_contactado',
        'mark_as_pago_pendiente',
        'mark_as_pago_completado',
        'generate_registration_links',
    ]

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
        progress = obj.get_timeline_progress()

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

    # URLs personalizadas
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:registration_id>/advance/',
                self.advance_status_view,
                name='advance_user_status'
            ),
            path(
                '<int:registration_id>/copy-link/',
                self.copy_link_view,
                name='copy_registration_link'
            ),
            path(
                'dashboard/',
                self.dashboard_view,
                name='user_management_dashboard'
            ),
        ]
        return custom_urls + urls

    def advance_status_view(self, request, registration_id):
        """Vista para avanzar estado de usuario"""
        registration = get_object_or_404(UserRegistration, pk=registration_id)

        if registration.advance_status():
            # Log de la acción
            UserRegistrationLog.objects.create(
                registration=registration,
                action=f'advanced_to_{registration.status}',
                description=f'Estado avanzado a: {registration.get_status_display()}',
                created_by=request.user if request.user.is_authenticated else None
            )

            messages.success(
                request,
                f'Usuario {registration.full_name} avanzado a: {registration.get_status_display()}'
            )
        else:
            messages.warning(
                request,
                f'No se puede avanzar más el estado de {registration.full_name}'
            )

        return redirect('admin:pos_userregistration_changelist')

    def copy_link_view(self, request, registration_id):
        """Vista para copiar link de registro"""
        registration = get_object_or_404(UserRegistration, pk=registration_id)

        if registration.registration_token and registration.is_token_valid():
            url = request.build_absolute_uri(f'/registro/complete/{registration.registration_token}/')

            return JsonResponse({
                'url': url,
                'message': 'Link copiado al portapapeles'
            })

        return JsonResponse({
            'error': 'No hay link válido para este usuario'
        }, status=400)

    def dashboard_view(self, request):
        """Dashboard con métricas del proceso"""
        # Esta será una vista personalizada con gráficos
        pass

    # Acciones en lote
    def mark_as_mensaje_enviado(self, request, queryset):
        updated = 0
        for registration in queryset:
            if registration.status == 'nuevo':
                registration.advance_status('mensaje_enviado')
                updated += 1

        self.message_user(
            request,
            f'{updated} usuarios marcados como "Mensaje enviado"'
        )
    mark_as_mensaje_enviado.short_description = '📱 Marcar como "Mensaje enviado"'

    def mark_as_contactado(self, request, queryset):
        updated = 0
        for registration in queryset:
            if registration.status == 'mensaje_enviado':
                registration.advance_status('contactado')
                updated += 1

        self.message_user(
            request,
            f'{updated} usuarios marcados como "Contactado"'
        )
    mark_as_contactado.short_description = '💬 Marcar como "Contactado"'

    def mark_as_pago_pendiente(self, request, queryset):
        updated = 0
        for registration in queryset:
            if registration.status == 'contactado':
                registration.advance_status('pago_pendiente')
                updated += 1

        self.message_user(
            request,
            f'{updated} usuarios marcados como "Pago pendiente"'
        )
    mark_as_pago_pendiente.short_description = '⏳ Marcar como "Pago pendiente"'

    def mark_as_pago_completado(self, request, queryset):
        updated = 0
        for registration in queryset:
            if registration.status == 'pago_pendiente':
                registration.advance_status('pago_completado')
                updated += 1

        self.message_user(
            request,
            f'{updated} usuarios marcados como "Pago completado" y links generados'
        )
    mark_as_pago_completado.short_description = '💰 Confirmar pago (genera links)'

    def generate_registration_links(self, request, queryset):
        updated = 0
        for registration in queryset:
            if registration.status == 'pago_completado' and not registration.registration_token:
                registration.generate_registration_token()
                registration.save()
                updated += 1

        self.message_user(
            request,
            f'{updated} links de registro generados'
        )
    generate_registration_links.short_description = '🔗 Generar links de registro'


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