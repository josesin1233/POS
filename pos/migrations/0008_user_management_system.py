# Generated manually for user management system

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),  # Adjust this if needed
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('pos', '0007_auto_20241028_1654'),  # Adjust to your last migration
    ]

    operations = [
        migrations.CreateModel(
            name='UserRegistration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('full_name', models.CharField(max_length=100, verbose_name='Nombre completo')),
                ('email', models.EmailField(max_length=254, unique=True, verbose_name='Email')),
                ('phone', models.CharField(max_length=20, verbose_name='Teléfono')),
                ('city', models.CharField(max_length=50, verbose_name='Ciudad')),
                ('status', models.CharField(choices=[('nuevo', '🆕 Nuevo Lead'), ('mensaje_enviado', '📱 Mensaje Enviado'), ('contactado', '💬 Contactado'), ('pago_pendiente', '⏳ Pago Pendiente'), ('pago_completado', '💰 Pago Completado'), ('link_enviado', '🔗 Link Enviado'), ('registro_completo', '✅ Registro Completo'), ('activo', '🚀 Usuario Activo'), ('vencido', '⚠️ Suscripción Vencida'), ('cancelado', '❌ Cancelado')], default='nuevo', max_length=20, verbose_name='Estado')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Fecha de registro')),
                ('mensaje_enviado_at', models.DateTimeField(blank=True, null=True, verbose_name='Mensaje enviado')),
                ('contactado_at', models.DateTimeField(blank=True, null=True, verbose_name='Contactado')),
                ('pago_pendiente_at', models.DateTimeField(blank=True, null=True, verbose_name='Pago pendiente desde')),
                ('pago_completado_at', models.DateTimeField(blank=True, null=True, verbose_name='Pago completado')),
                ('link_enviado_at', models.DateTimeField(blank=True, null=True, verbose_name='Link enviado')),
                ('registro_completo_at', models.DateTimeField(blank=True, null=True, verbose_name='Registro completado')),
                ('registration_token', models.UUIDField(blank=True, null=True, unique=True, verbose_name='Token de registro')),
                ('token_expires_at', models.DateTimeField(blank=True, null=True, verbose_name='Token expira')),
                ('token_used', models.BooleanField(default=False, verbose_name='Token usado')),
                ('token_used_at', models.DateTimeField(blank=True, null=True, verbose_name='Token usado en')),
                ('notes', models.TextField(blank=True, verbose_name='Notas administrativas')),
                ('source', models.CharField(default='formulario_web', max_length=50, verbose_name='Origen')),
                ('business', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.business', verbose_name='Negocio')),
                ('pos_user', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='Usuario POS')),
            ],
            options={
                'verbose_name': 'Registro de Usuario',
                'verbose_name_plural': 'Gestión de Usuarios',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='UserRegistrationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=50)),
                ('description', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('registration', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logs', to='pos.userregistration')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]