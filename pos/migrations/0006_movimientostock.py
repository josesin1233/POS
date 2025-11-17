# Generated manually for MovimientoStock model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0001_initial'),
        ('pos', '0005_caja_suscripcion_alter_resumendiario_unique_together_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='MovimientoStock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo_movimiento', models.CharField(choices=[('entrada', 'Entrada'), ('salida', 'Salida'), ('ajuste', 'Ajuste'), ('venta', 'Venta'), ('compra', 'Compra'), ('devolucion', 'Devolución'), ('merma', 'Merma')], max_length=20)),
                ('cantidad', models.IntegerField(help_text='Cantidad de productos (positivo para entradas, negativo para salidas)')),
                ('stock_anterior', models.PositiveIntegerField(verbose_name='Stock antes del movimiento')),
                ('stock_nuevo', models.PositiveIntegerField(verbose_name='Stock después del movimiento')),
                ('motivo', models.CharField(blank=True, help_text='Descripción del movimiento', max_length=200, null=True)),
                ('fecha_movimiento', models.DateTimeField(auto_now_add=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP desde donde se hizo el movimiento')),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='movimientos_stock', to='accounts.business')),
                ('producto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='movimientos', to='pos.producto')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='movimientos_stock_realizados', to=settings.AUTH_USER_MODEL)),
                ('venta', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='movimientos_stock', to='pos.venta')),
            ],
            options={
                'verbose_name': 'Movimiento de Stock',
                'verbose_name_plural': 'Movimientos de Stock',
                'ordering': ['-fecha_movimiento'],
                'indexes': [
                    models.Index(fields=['business', 'fecha_movimiento'], name='pos_movimie_busines_a60e48_idx'),
                    models.Index(fields=['producto', 'fecha_movimiento'], name='pos_movimie_product_b3e965_idx'),
                    models.Index(fields=['business', 'tipo_movimiento'], name='pos_movimie_busines_ecc53e_idx'),
                    models.Index(fields=['venta'], name='pos_movimie_venta_i_5f6c6f_idx'),
                ],
            },
        ),
    ]