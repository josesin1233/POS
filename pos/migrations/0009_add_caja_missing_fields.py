# Generated manually to add missing fields to Caja model

from decimal import Decimal
from django.db import migrations, models
from django.utils import timezone


def set_default_fecha(apps, schema_editor):
    """Set fecha from fecha_apertura for existing Caja records"""
    Caja = apps.get_model('pos', 'Caja')
    for caja in Caja.objects.all():
        if hasattr(caja, 'fecha_apertura') and caja.fecha_apertura:
            caja.fecha = caja.fecha_apertura.date()
            caja.save(update_fields=['fecha'])


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0008_user_management_system'),
    ]

    operations = [
        # Add missing fields to Caja with temporary null=True
        migrations.AddField(
            model_name='caja',
            name='fecha',
            field=models.DateField(null=True, blank=True),
        ),
        # Populate fecha from fecha_apertura for existing records
        migrations.RunPython(set_default_fecha, reverse_code=migrations.RunPython.noop),
        # Make fecha non-nullable now that it has values
        migrations.AlterField(
            model_name='caja',
            name='fecha',
            field=models.DateField(default=timezone.now),
        ),
        migrations.AddField(
            model_name='caja',
            name='monto_actual',
            field=models.DecimalField(
                max_digits=10,
                decimal_places=2,
                default=Decimal('0.00')
            ),
        ),
        migrations.AddField(
            model_name='caja',
            name='efectivo_real',
            field=models.DecimalField(
                max_digits=10,
                decimal_places=2,
                null=True,
                blank=True
            ),
        ),
        migrations.AddField(
            model_name='caja',
            name='hora_cierre',
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
