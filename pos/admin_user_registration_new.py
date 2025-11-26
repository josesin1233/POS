"""
Admin optimizado para gestión rápida de leads
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from .models import UserRegistration, UserRegistrationLog
from urllib.parse import quote


class UserRegistrationAdmin(admin.ModelAdmin):
    """Admin optimizado para gestión rápida de leads"""

    # SOLO LO ESENCIAL EN LA TABLA
    list_display = [
        'full_name',
        'email',
        'phone_display',
        'city',
        'progress_bar',
        'whatsapp_button',
    ]

    list_filter = ['status', 'created_at']
    search_fields = ['full_name', 'email', 'phone']
    ordering = ['-created_at']

    # Media para estilos y scripts
    class Media:
        css = {
            'all': ('admin/css/lead_management.css',)
        }
        js = ('admin/js/lead_management.js',)

    def phone_display(self, obj):
        """Teléfono clickeable que copia al portapapeles"""
        return format_html(
            '<span class="phone-copy" data-phone="{}" data-lead-id="{}" style="cursor: pointer; color: #667eea; font-weight: 600;">'
            '📱 {}</span>',
            obj.phone,
            obj.pk,
            obj.phone
        )
    phone_display.short_description = 'Teléfono'

    def progress_bar(self, obj):
        """Barra de progreso interactiva"""
        # Definir los estados y su orden
        stages = [
            ('nuevo', 'Nuevo'),
            ('mensaje_enviado', 'Mensaje'),
            ('contactado', 'Contactado'),
            ('pago_pendiente', 'Pago Pdte'),
            ('pago_completado', 'Pagado'),
            ('link_enviado', 'Link'),
            ('registro_completo', 'Completo'),
        ]

        # Calcular progreso
        current_index = next((i for i, (key, _) in enumerate(stages) if key == obj.status), 0)
        progress_percent = int((current_index / (len(stages) - 1)) * 100) if len(stages) > 1 else 0

        # Link de registro si está disponible
        registration_link_html = ''
        if obj.registration_token and obj.is_token_valid():
            protocol = 'https'
            domain = 'web-production-11df5.up.railway.app'  # Tu dominio
            full_url = f"{protocol}://{domain}/registro/complete/{obj.registration_token}/"
            registration_link_html = f'''
                <button class="copy-link-btn" data-url="{full_url}" 
                        style="margin-left: 10px; padding: 4px 12px; background: #48bb78; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 11px;">
                    📋 Copiar Link
                </button>
            '''

        html = f'''
        <div class="progress-container" data-lead-id="{obj.pk}" data-current-status="{obj.status}">
            <div class="progress-bar-wrapper">
                <div class="progress-bar-fill" style="width: {progress_percent}%;"></div>
                <div class="progress-text">{obj.get_status_display()}</div>
            </div>
            <select class="status-selector" data-lead-id="{obj.pk}">
        '''

        for status_key, status_label in stages:
            selected = 'selected' if status_key == obj.status else ''
            html += f'<option value="{status_key}" {selected}>{status_label}</option>'

        html += f'''
            </select>
            {registration_link_html}
        </div>
        '''

        return format_html(html)
    progress_bar.short_description = 'Progreso'

    def whatsapp_button(self, obj):
        """Botón para abrir WhatsApp con mensaje predefinido"""
        # Limpiar número (quitar espacios, guiones, etc.)
        phone_clean = ''.join(filter(str.isdigit, obj.phone))
        
        # Si no tiene código de país, asumir México (+52)
        if not phone_clean.startswith('52') and len(phone_clean) == 10:
            phone_clean = '52' + phone_clean

        # Mensaje predefinido
        message = f"""¡Hola {obj.full_name}! 👋

Gracias por tu interés en POS México.

Para completar tu registro necesito la siguiente información:

1️⃣ Tipo de negocio:
2️⃣ Plan que deseas (Básico/Premium):
3️⃣ Forma de pago preferida:

¿Cuándo podemos agendar una llamada rápida?"""

        whatsapp_url = f"https://wa.me/{phone_clean}?text={quote(message)}"

        return format_html(
            '<a href="{}" target="_blank" class="whatsapp-btn" data-lead-id="{}">'
            '<img src="https://upload.wikimedia.org/wikipedia/commons/6/6b/WhatsApp.svg" '
            'style="width: 24px; height: 24px; vertical-align: middle;"> '
            'WhatsApp'
            '</a>',
            whatsapp_url,
            obj.pk
        )
    whatsapp_button.short_description = 'Contactar'

    def get_urls(self):
        """URLs personalizadas"""
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:pk>/update-status/',
                self.admin_site.admin_view(self.update_status_view),
                name='userregistration-update-status',
            ),
        ]
        return custom_urls + urls

    def update_status_view(self, request, pk):
        """Actualizar estado vía AJAX"""
        if request.method == 'POST':
            import json
            data = json.loads(request.body)
            new_status = data.get('status')

            registration = get_object_or_404(UserRegistration, pk=pk)
            old_status = registration.status

            registration.status = new_status
            registration.save()

            # Crear log
            UserRegistrationLog.objects.create(
                registration=registration,
                action='status_change',
                description=f'Estado cambiado de "{old_status}" a "{new_status}"',
                created_by=request.user
            )

            # Si llega a pago_completado, generar token
            if new_status == 'pago_completado' and not registration.registration_token:
                registration.generate_registration_token()
                registration.save()

            return JsonResponse({'success': True, 'new_status': new_status})

        return JsonResponse({'error': 'Método no permitido'}, status=405)
