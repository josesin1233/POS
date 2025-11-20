# Generated manually for subscription models

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('pos', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SubscriptionPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
                ('display_name', models.CharField(max_length=100)),
                ('description', models.TextField(blank=True)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('max_concurrent_users', models.IntegerField(default=2)),
                ('duration_days', models.IntegerField(default=30)),
                ('hierarchy_level', models.IntegerField(default=1)),
                ('is_active', models.BooleanField(default=True)),
                ('is_promotional', models.BooleanField(default=False)),
                ('promotional_text', models.CharField(blank=True, max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Plan de Suscripción',
                'verbose_name_plural': 'Planes de Suscripción',
                'ordering': ['hierarchy_level', 'price'],
            },
        ),
        migrations.CreateModel(
            name='PlanFeature',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('description', models.TextField()),
                ('feature_key', models.CharField(max_length=50)),
                ('display_order', models.IntegerField(default=1)),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='features', to='pos.subscriptionplan')),
            ],
            options={
                'verbose_name': 'Característica del Plan',
                'verbose_name_plural': 'Características del Plan',
                'ordering': ['display_order'],
            },
        ),
        migrations.CreateModel(
            name='PaymentTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transaction_id', models.CharField(max_length=200, unique=True)),
                ('gateway_transaction_id', models.CharField(blank=True, max_length=200, null=True)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('currency', models.CharField(default='MXN', max_length=3)),
                ('gateway', models.CharField(choices=[('stripe', 'Stripe'), ('paypal', 'PayPal'), ('mercadopago', 'Mercado Pago'), ('manual', 'Manual')], max_length=20)),
                ('payment_method', models.CharField(blank=True, max_length=50)),
                ('status', models.CharField(choices=[('pending', 'Pendiente'), ('processing', 'Procesando'), ('completed', 'Completado'), ('failed', 'Fallido'), ('refunded', 'Reembolsado'), ('cancelled', 'Cancelado')], default='pending', max_length=20)),
                ('gateway_response', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_transactions', to='accounts.business')),
                ('plan', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='pos.subscriptionplan')),
                ('subscription', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payment_transactions', to='pos.suscripcion')),
            ],
            options={
                'verbose_name': 'Transacción de Pago',
                'verbose_name_plural': 'Transacciones de Pago',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='SubscriptionRegistration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('business_name', models.CharField(max_length=100)),
                ('business_type', models.CharField(max_length=50)),
                ('address', models.TextField()),
                ('state', models.CharField(max_length=50)),
                ('country', models.CharField(default='México', max_length=50)),
                ('contact_email', models.EmailField(max_length=254)),
                ('contact_phone', models.CharField(max_length=15)),
                ('admin_username', models.CharField(max_length=150)),
                ('admin_password', models.CharField(max_length=200)),
                ('admin_first_name', models.CharField(max_length=150)),
                ('admin_last_name', models.CharField(max_length=150)),
                ('is_completed', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('payment_transaction', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='pos.paymenttransaction')),
                ('selected_plan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='pos.subscriptionplan')),
            ],
            options={
                'verbose_name': 'Registro de Suscripción',
                'verbose_name_plural': 'Registros de Suscripción',
                'ordering': ['-created_at'],
            },
        ),
    ]