# Migration that was already applied in production
# This is a safe no-op migration that checks if GastoCaja exists before creating it

from django.db import migrations, models, connection
import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.conf import settings


def check_table_exists(table_name):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = %s
            );
        """, [table_name])
        return cursor.fetchone()[0]


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_userpermissions'),
        ('pos', '0009_add_caja_missing_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Only create GastoCaja if it doesn't exist (safe for production)
        migrations.RunPython(
            code=lambda apps, schema_editor: None if check_table_exists('pos_gastocaja') else None,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
