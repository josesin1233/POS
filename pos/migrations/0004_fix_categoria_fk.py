# Generated manually to fix categoria field type and create missing models
import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_auto_20250808_1522'),
        ('pos', '0003_auto_20250808_1523'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # First, create the Categoria model
        migrations.CreateModel(
            name='Categoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100)),
                ('descripcion', models.TextField(blank=True, null=True)),
                ('activa', models.BooleanField(default=True)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='categorias', to='accounts.business')),
            ],
            options={
                'verbose_name': 'Categoría',
                'verbose_name_plural': 'Categorías',
                'ordering': ['business', 'nombre'],
            },
        ),
        
        # Create Sucursal model (referenced by other models)
        migrations.CreateModel(
            name='Sucursal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=200, verbose_name='Nombre de la sucursal')),
                ('direccion', models.TextField(blank=True, null=True)),
                ('telefono', models.CharField(blank=True, max_length=15, null=True)),
                ('encargado', models.CharField(blank=True, max_length=200, null=True)),
                ('activa', models.BooleanField(default=True)),
                ('es_principal', models.BooleanField(default=False)),
                ('ips_permitidas', models.TextField(blank=True, help_text='IPs separadas por comas. Vacío = cualquier IP', null=True)),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('fecha_modificacion', models.DateTimeField(auto_now=True)),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sucursales', to='accounts.business')),
            ],
            options={
                'verbose_name': 'Sucursal',
                'verbose_name_plural': 'Sucursales',
                'ordering': ['business', 'nombre'],
            },
        ),
        
        # Add unique constraint to Categoria
        migrations.AlterUniqueTogether(
            name='categoria',
            unique_together={('business', 'nombre')},
        ),
        
        # Add unique constraint to Sucursal
        migrations.AlterUniqueTogether(
            name='sucursal',
            unique_together={('business', 'nombre')},
        ),

        # Now remove the old categoria CharField
        migrations.RemoveField(
            model_name='producto',
            name='categoria',
        ),
        
        # Add missing fields to Producto to match current model
        migrations.AddField(
            model_name='producto',
            name='descripcion',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='producto',
            name='precio_compra',
            field=models.DecimalField(
                blank=True, 
                decimal_places=2, 
                max_digits=10, 
                null=True, 
                validators=[django.core.validators.MinValueValidator(Decimal('0.01'))], 
                verbose_name='Precio de compra'
            ),
        ),
        migrations.AddField(
            model_name='producto',
            name='stock_maximo',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='Stock máximo'),
        ),
        migrations.AddField(
            model_name='producto',
            name='activo',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='producto',
            name='requiere_peso',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='producto',
            name='permite_decimales',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='producto',
            name='porcentaje_impuesto',
            field=models.DecimalField(
                decimal_places=2, 
                default=Decimal('0.00'), 
                max_digits=5, 
                validators=[django.core.validators.MinValueValidator(Decimal('0')), django.core.validators.MaxValueValidator(Decimal('100'))]
            ),
        ),
        migrations.AddField(
            model_name='producto',
            name='fecha_creacion',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='producto',
            name='fecha_modificacion',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        
        # Add the new categoria ForeignKey
        migrations.AddField(
            model_name='producto',
            name='categoria',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='productos',
                to='pos.categoria'
            ),
        ),
        
        # Rename created_by to creado_por to match model
        migrations.RenameField(
            model_name='producto',
            old_name='created_by',
            new_name='creado_por',
        ),
        
        # Update field attributes to match current model
        migrations.AlterField(
            model_name='producto',
            name='codigo',
            field=models.CharField(max_length=50, verbose_name='Código de barras'),
        ),
        migrations.AlterField(
            model_name='producto',
            name='nombre',
            field=models.CharField(max_length=200, verbose_name='Nombre del producto'),
        ),
        migrations.AlterField(
            model_name='producto',
            name='precio',
            field=models.DecimalField(
                decimal_places=2, 
                max_digits=10, 
                validators=[django.core.validators.MinValueValidator(Decimal('0.01'))], 
                verbose_name='Precio de venta'
            ),
        ),
        migrations.AlterField(
            model_name='producto',
            name='stock',
            field=models.PositiveIntegerField(default=0, verbose_name='Stock actual'),
        ),
        migrations.AlterField(
            model_name='producto',
            name='stock_minimo',
            field=models.PositiveIntegerField(default=10, verbose_name='Stock mínimo'),
        ),
        
        # Remove old created_at field and add indexes
        migrations.RemoveField(
            model_name='producto',
            name='created_at',
        ),
        
        # Add database indexes for performance
        migrations.AddIndex(
            model_name='producto',
            index=models.Index(fields=['business', 'codigo'], name='pos_producto_bus_codigo_idx'),
        ),
        migrations.AddIndex(
            model_name='producto',
            index=models.Index(fields=['business', 'nombre'], name='pos_producto_bus_nombre_idx'),
        ),
        migrations.AddIndex(
            model_name='producto',
            index=models.Index(fields=['business', 'activo'], name='pos_producto_bus_activo_idx'),
        ),
    ]