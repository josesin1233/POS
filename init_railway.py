#!/usr/bin/env python
"""
Script de inicialización para Railway
Este script crea los datos iniciales necesarios para la aplicación
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dulceria_pos.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import Business, UserPermissions
from pos.models import Producto

User = get_user_model()

def create_superuser():
    """Crear superusuario si no existe"""
    if not User.objects.filter(username='admin').exists():
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@dulceria.com',
            password='admin123456',
            first_name='Administrador',
            last_name='Sistema'
        )
        print(f"✅ Superusuario creado: admin/admin123456")
        return admin_user
    else:
        print("ℹ️ Superusuario ya existe")
        return User.objects.get(username='admin')

def create_demo_business():
    """Crear negocio demo si no existe"""
    business, created = Business.objects.get_or_create(
        name='Dulcería Demo',
        defaults={
            'address': 'Calle Principal #123',
            'phone': '+52-555-1234567',
            'email': 'demo@dulceria.com'
        }
    )
    if created:
        print(f"✅ Negocio demo creado: {business.name}")
    else:
        print(f"ℹ️ Negocio demo ya existe: {business.name}")
    return business

def create_demo_user(business):
    """Crear usuario demo si no existe"""
    demo_user, created = User.objects.get_or_create(
        username='demo',
        defaults={
            'email': 'demo@dulceria.com',
            'first_name': 'Usuario',
            'last_name': 'Demo',
            'is_active': True
        }
    )
    
    if created:
        demo_user.set_password('demo123456')
        demo_user.save()
        print(f"✅ Usuario demo creado: demo/demo123456")
    else:
        print(f"ℹ️ Usuario demo ya existe")
    
    # Asignar negocio al usuario y crear permisos
    demo_user.business = business
    demo_user.is_business_owner = True
    demo_user.save()
    
    # Crear permisos de administrador
    permissions, created = UserPermissions.objects.get_or_create(
        user=demo_user,
        business=business,
        defaults={}
    )
    
    if created:
        UserPermissions.create_default_permissions(demo_user, business, is_owner=True)
        print(f"✅ Usuario demo asignado al negocio con permisos de administrador")
    
    return demo_user

def create_demo_products(business):
    """Crear productos demo si no existen"""
    demo_products = [
        {
            'codigo': 'CHI001',
            'nombre': 'Chicle Trident Menta',
            'precio': 5.50,
            'stock': 25,
            'stock_minimo': 10,
            'categoria': 'Chicles'
        },
        {
            'codigo': 'CHO001', 
            'nombre': 'Chocolate Carlos V',
            'precio': 12.00,
            'stock': 5,  # Bajo stock para probar alertas
            'stock_minimo': 15,
            'categoria': 'Chocolates'
        },
        {
            'codigo': 'DUL001',
            'nombre': 'Dulce Enchilado',
            'precio': 8.00,
            'stock': 30,
            'stock_minimo': 10,
            'categoria': 'Dulces'
        },
        {
            'codigo': 'REF001',
            'nombre': 'Coca Cola 600ml',
            'precio': 18.00,
            'stock': 2,  # Muy bajo stock
            'stock_minimo': 20,
            'categoria': 'Refrescos'
        },
        {
            'codigo': 'GAL001',
            'nombre': 'Galletas Marías',
            'precio': 15.50,
            'stock': 40,
            'stock_minimo': 12,
            'categoria': 'Galletas'
        }
    ]
    
    created_count = 0
    for product_data in demo_products:
        product, created = Producto.objects.get_or_create(
            codigo=product_data['codigo'],
            business=business,
            defaults=product_data
        )
        if created:
            created_count += 1
    
    if created_count > 0:
        print(f"✅ {created_count} productos demo creados")
    else:
        print("ℹ️ Productos demo ya existen")

def main():
    """Función principal de inicialización"""
    print("🚀 Iniciando configuración de Railway...")
    
    try:
        # Crear superusuario
        admin_user = create_superuser()
        
        # Crear negocio demo
        business = create_demo_business()
        
        # Crear usuario demo
        demo_user = create_demo_user(business)
        
        # Crear productos demo
        create_demo_products(business)
        
        print("\n✅ Configuración completada exitosamente!")
        print("\n📋 Credenciales de acceso:")
        print("   👤 Superusuario: admin / admin123456")
        print("   🏪 Usuario demo: demo / demo123456")
        print(f"   🌐 Business: {business.name}")
        print("\n🔗 Accede a /admin/ para administración")
        print("🔗 Accede a /accounts/login/ para el POS")
        
    except Exception as e:
        print(f"❌ Error durante la inicialización: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()