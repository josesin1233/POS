from django.contrib import admin 
from .models import Producto, Venta, VentaDetalle, Categoria, Sucursal
from django.utils.html import format_html

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
