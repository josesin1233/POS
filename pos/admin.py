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
            path(
                'add-manual/',
                self.admin_site.admin_view(self.add_lead_manual_view),
                name='add_lead_manual',
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

    def add_lead_manual_view(self, request):
        """Crear usuario nuevo (Business Owner o Employee) desde el dashboard"""
        if request.method == 'POST':
            try:
                from accounts.models import Business, User, UserPermissions
                from django.contrib.auth.hashers import make_password
                from datetime import date
                from dateutil.relativedelta import relativedelta

                # Datos básicos
                user_type = request.POST.get('user_type', '').strip()
                full_name = request.POST.get('full_name', '').strip()
                email = request.POST.get('email', '').strip()
                username = request.POST.get('username', '').strip()
                password = request.POST.get('password', '').strip()

                # Validaciones básicas
                if not all([user_type, full_name, email, username, password]):
                    return JsonResponse({
                        'success': False,
                        'error': 'Todos los campos obligatorios deben completarse'
                    }, status=400)

                # Verificar si username o email ya existen
                if User.objects.filter(username=username).exists():
                    return JsonResponse({
                        'success': False,
                        'error': 'El nombre de usuario ya existe'
                    }, status=400)

                if User.objects.filter(email=email).exists():
                    return JsonResponse({
                        'success': False,
                        'error': 'El email ya está registrado'
                    }, status=400)

                # Procesar según tipo de usuario
                if user_type == 'owner':
                    # Business Owner - crear negocio y usuario
                    phone = request.POST.get('phone', '').strip()
                    city = request.POST.get('city', '').strip()
                    business_name = request.POST.get('business_name', '').strip()

                    if not business_name or not phone:
                        return JsonResponse({
                            'success': False,
                            'error': 'Nombre del negocio y teléfono son obligatorios para Business Owner'
                        }, status=400)

                    # Crear el negocio
                    business = Business.objects.create(
                        name=business_name,
                        email=email,
                        phone=phone,
                        address=city or '',
                        subscription_active=True
                    )

                    # Crear el usuario owner
                    user = User.objects.create(
                        username=username,
                        email=email,
                        first_name=full_name.split()[0] if full_name.split() else full_name,
                        last_name=' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else '',
                        password=make_password(password),
                        phone=phone,
                        business=business,
                        is_business_owner=True,
                        is_staff=False,
                        is_active=True
                    )

                    # Crear permisos de owner
                    UserPermissions.create_default_permissions(user, business, is_owner=True)

                    # Crear registro de lead con datos de contrato
                    lead_data = {
                        'full_name': full_name,
                        'email': email,
                        'phone': phone,
                        'city': city,
                        'status': 'activo',
                        'business': business
                    }

                    # Procesar datos de contrato si existen
                    meses_contratados = request.POST.get('meses_contratados', '').strip()
                    monto_pagado = request.POST.get('monto_pagado', '').strip()

                    if meses_contratados:
                        meses = int(meses_contratados)
                        fecha_inicio = date.today()
                        fecha_corte = fecha_inicio + relativedelta(months=meses)
                        lead_data['meses_contratados'] = meses
                        lead_data['fecha_inicio_contrato'] = fecha_inicio
                        lead_data['fecha_corte'] = fecha_corte

                    if monto_pagado:
                        lead_data['monto_pagado'] = float(monto_pagado)

                    lead = UserRegistration.objects.create(**lead_data)

                    # Crear log
                    UserRegistrationLog.objects.create(
                        registration=lead,
                        action='manual_creation',
                        description=f'Business Owner creado por {request.user.username}',
                        created_by=request.user
                    )

                    return JsonResponse({
                        'success': True,
                        'message': f'Business Owner {full_name} y negocio {business_name} creados exitosamente'
                    })

                elif user_type == 'employee':
                    # Employee - vincular a negocio existente
                    business_id = request.POST.get('business_id', '').strip()

                    if not business_id:
                        return JsonResponse({
                            'success': False,
                            'error': 'Debe seleccionar un negocio para el empleado'
                        }, status=400)

                    try:
                        business = Business.objects.get(id=business_id)
                    except Business.DoesNotExist:
                        return JsonResponse({
                            'success': False,
                            'error': 'El negocio seleccionado no existe'
                        }, status=400)

                    # Crear el usuario employee
                    user = User.objects.create(
                        username=username,
                        email=email,
                        first_name=full_name.split()[0] if full_name.split() else full_name,
                        last_name=' '.join(full_name.split()[1:]) if len(full_name.split()) > 1 else '',
                        password=make_password(password),
                        business=business,
                        is_business_owner=False,
                        is_staff=False,
                        is_active=True
                    )

                    # Crear permisos de employee
                    UserPermissions.create_default_permissions(user, business, is_owner=False)

                    return JsonResponse({
                        'success': True,
                        'message': f'Empleado {full_name} agregado exitosamente a {business.name}'
                    })

                else:
                    return JsonResponse({
                        'success': False,
                        'error': 'Tipo de usuario inválido'
                    }, status=400)

            except Exception as e:
                import traceback
                traceback.print_exc()
                return JsonResponse({
                    'success': False,
                    'error': f'Error al crear el usuario: {str(e)}'
                }, status=500)

        return JsonResponse({'error': 'Método no permitido'}, status=405)



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

    def get_urls(self):
        """URLs personalizadas del admin site"""
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('add_lead_manual/', self.admin_view(self.add_lead_manual_view), name='add_lead_manual'),
            path('get_businesses/', self.admin_view(self.get_businesses_view), name='get_businesses'),
        ]
        return custom_urls + urls

    def get_businesses_view(self, request):
        """Obtener lista de negocios para el select"""
        if request.method == 'GET':
            try:
                from accounts.models import Business
                businesses = Business.objects.filter(subscription_active=True).order_by('name')

                business_list = [
                    {'id': b.id, 'name': b.name}
                    for b in businesses
                ]

                return JsonResponse({
                    'success': True,
                    'businesses': business_list
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=500)

        return JsonResponse({'error': 'Método no permitido'}, status=405)

    def add_lead_manual_view(self, request):
        """Agregar lead manualmente desde el dashboard"""
        if request.method == 'POST':
            try:
                from datetime import date
                from dateutil.relativedelta import relativedelta

                full_name = request.POST.get('full_name', '').strip()
                email = request.POST.get('email', '').strip()
                phone = request.POST.get('phone', '').strip()
                city = request.POST.get('city', '').strip()

                # Campos de pago (pueden ser vacíos si es usuario sin cobro)
                meses_contratados = request.POST.get('meses_contratados', '').strip()
                monto_pagado = request.POST.get('monto_pagado', '').strip()

                # Validaciones básicas
                if not full_name or not email or not phone:
                    return JsonResponse({
                        'success': False,
                        'error': 'Nombre, email y teléfono son obligatorios'
                    }, status=400)

                # Verificar si el email ya existe
                if UserRegistration.objects.filter(email=email).exists():
                    return JsonResponse({
                        'success': False,
                        'error': 'Ya existe un lead con este email'
                    }, status=400)

                # Preparar datos del lead
                lead_data = {
                    'full_name': full_name,
                    'email': email,
                    'phone': phone,
                    'city': city,
                    'status': 'nuevo',
                    'source': 'manual_admin'
                }

                # Si tiene meses contratados, calcular fechas automáticamente
                if meses_contratados:
                    meses = int(meses_contratados)
                    fecha_inicio = date.today()
                    # Usar relativedelta para sumar meses correctamente
                    fecha_corte = fecha_inicio + relativedelta(months=meses)

                    lead_data['meses_contratados'] = meses
                    lead_data['fecha_inicio_contrato'] = fecha_inicio
                    lead_data['fecha_corte'] = fecha_corte

                # Si tiene monto pagado, guardarlo
                if monto_pagado:
                    lead_data['monto_pagado'] = float(monto_pagado)

                # Crear el lead
                lead = UserRegistration.objects.create(**lead_data)

                # Crear log
                log_desc = f'Lead creado manualmente por {request.user.username}'
                if meses_contratados:
                    log_desc += f' - Contrato: {meses_contratados} meses hasta {lead.fecha_corte}'
                if monto_pagado:
                    log_desc += f' - Monto: ${monto_pagado}'

                UserRegistrationLog.objects.create(
                    registration=lead,
                    action='manual_creation',
                    description=log_desc,
                    created_by=request.user
                )

                return JsonResponse({
                    'success': True,
                    'message': f'Lead {full_name} agregado exitosamente'
                })

            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': f'Error al crear el lead: {str(e)}'
                }, status=500)

        return JsonResponse({'error': 'Método no permitido'}, status=405)

    def index(self, request, extra_context=None):
        """Dashboard personalizado con estadísticas"""
        from .models import UserRegistration, Venta, Producto
        from accounts.models import User, Business
        from django.db.models import Sum, Count, F
        from datetime import date, timedelta

        # Estadísticas de usuarios del sistema (User model)
        total_businesses = Business.objects.count()
        total_users_system = User.objects.count()

        # Estadísticas del proceso de registro (UserRegistration model)
        total_registros = UserRegistration.objects.count()
        usuarios_nuevos = UserRegistration.objects.filter(status='nuevo').count()
        usuarios_pago = UserRegistration.objects.filter(
            status__in=['pago_pendiente', 'pago_completado']
        ).count()
        usuarios_activos_registros = UserRegistration.objects.filter(status='activo').count()

        # Contar por cada estado para debugging
        status_counts = {}
        for status_key, status_label in UserRegistration.STATUS_CHOICES:
            count = UserRegistration.objects.filter(status=status_key).count()
            if count > 0:
                status_counts[status_label] = count

        # Últimos 5 registros
        ultimos_usuarios = UserRegistration.objects.order_by('-created_at')[:5]

        # Usuarios próximos a vencer (ordenados por fecha de corte, más próximos primero)
        # Solo incluir usuarios que tienen fecha_corte (excluyendo usuarios sin cobro)
        usuarios_proximos_vencer = UserRegistration.objects.filter(
            fecha_corte__isnull=False
        ).select_related('business').order_by('fecha_corte')

        # Calcular días restantes para cada usuario
        hoy = date.today()
        for usuario in usuarios_proximos_vencer:
            if usuario.fecha_corte:
                delta = usuario.fecha_corte - hoy
                usuario.dias_restantes = delta.days

        context = {
            **self.each_context(request),
            'total_usuarios': total_businesses,  # Negocios registrados
            'usuarios_nuevos': usuarios_nuevos,
            'usuarios_pago': usuarios_pago,
            'usuarios_activos': total_users_system,  # Usuarios del sistema
            'ultimos_usuarios': ultimos_usuarios,
            'status_counts': status_counts,  # Para debugging
            'total_registros': total_registros,
            'usuarios_proximos_vencer': usuarios_proximos_vencer,  # Nueva lista
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
