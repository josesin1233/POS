# Generated manually to add missing fields to Caja model and create GastoCaja model

from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_userpermissions'),
        ('pos', '0008_user_management_system'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Add missing fields to Caja
        migrations.AddField(
            model_name='caja',
            name='fecha',
            field=models.DateField(auto_now_add=True, default=timezone.now),
            preserve_default=False,
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

        # Create GastoCaja model
        migrations.CreateModel(
            name='GastoCaja',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('concepto', models.CharField(max_length=200, verbose_name='Concepto del gasto')),
                ('monto', models.DecimalField(
                    max_digits=10,
                    decimal_places=2,
                    validators=[MinValueValidator(Decimal('0.01'))]
                )),
                ('tipo', models.CharField(
                    max_length=20,
                    choices=[
                        ('compra', 'Compra'),
                        ('gasto_operativo', 'Gasto Operativo'),
                        ('retiro', 'Retiro'),
                        ('otro', 'Otro'),
                    ],
                    default='otro'
                )),
                ('fecha', models.DateTimeField(auto_now_add=True)),
                ('business', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='gastos_caja',
                    to='accounts.business'
                )),
                ('usuario', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='gastos_realizados',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'verbose_name': 'Gasto de Caja',
                'verbose_name_plural': 'Gastos de Caja',
                'ordering': ['-fecha'],
            },
        ),

        # Add indexes to GastoCaja
        migrations.AddIndex(
            model_name='gastocaja',
            index=models.Index(fields=['business', 'fecha'], name='pos_gastoca_busines_a1b2c3_idx'),
        ),
        migrations.AddIndex(
            model_name='gastocaja',
            index=models.Index(fields=['business', 'tipo'], name='pos_gastoca_busines_d4e5f6_idx'),
        ),
    ]
