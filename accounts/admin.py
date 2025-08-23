from django.contrib import admin 
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import Business, User 
from django.utils.html import format_html

@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan_display', 'email', 'subscription_active', 'created_at', 'users_count', 'productos_count']
    list_filter = ['plan_actual', 'subscription_active', 'created_at']
    search_fields = ['name', 'email']
    list_editable = ['subscription_active']
    ordering = ['-created_at']
    list_per_page = 25
    
    fieldsets = (
        ('Información del Negocio', {
            'fields': ('name', 'email', 'phone', 'address', 'plan_actual', 'subscription_active')
        }),
        ('Configuración', {
            'fields': ('max_concurrent_users', 'monthly_cost'),
            'classes': ('collapse',)
        }),
    )
    
    def plan_display(self, obj):
        colors = {
            'basico': 'blue',
            'intermedio': 'green', 
            'profesional': 'purple'
        }
        color = colors.get(obj.plan_actual, 'gray')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', 
                          color, obj.get_plan_display())
    plan_display.short_description = "Plan"
    
    def users_count(self, obj):
        count = obj.user_set.count()
        max_users = obj.max_concurrent_users
        if count >= max_users:
            color = 'red'
        elif count >= max_users * 0.8:
            color = 'orange'
        else:
            color = 'green'
        return format_html('<span style="color: {};">{}/{}</span>', color, count, max_users)
    users_count.short_description = "Usuarios"
    
    def productos_count(self, obj):
        count = obj.productos.count() if hasattr(obj, 'productos') else 0
        return format_html('<span style="color: green;">{}</span>', count)
    productos_count.short_description = "Productos"

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Use Django's built-in UserCreationForm and UserChangeForm
    add_form = UserCreationForm
    form = UserChangeForm
    
    list_display = ['username', 'email', 'full_name', 'business', 'is_business_owner', 'is_active', 'last_login_display']
    list_filter = ['is_active', 'is_business_owner', 'business', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    list_editable = ['is_active']
    ordering = ['-date_joined']
    list_per_page = 50
    
    # Fieldsets for editing existing users
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Información Personal', {
            'fields': ('first_name', 'last_name', 'email', 'phone')
        }),
        ('Permisos', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_business_owner', 'business', 'groups', 'user_permissions')
        }),
        ('Fechas Importantes', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    # Fieldsets for adding new users (includes password fields)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2'),
        }),
        ('Información Personal', {
            'fields': ('first_name', 'last_name', 'email', 'phone')
        }),
        ('Permisos', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_business_owner', 'business')
        }),
    )
    
    def full_name(self, obj):
        return obj.get_full_name() or obj.username
    full_name.short_description = "Nombre Completo"
    
    def last_login_display(self, obj):
        if not obj.last_login:
            return format_html('<span style="color: gray;">Nunca</span>')
        return obj.last_login.strftime("%Y-%m-%d %H:%M")
    last_login_display.short_description = "Último Acceso"
