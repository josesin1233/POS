# Merge migration to resolve conflict between two 0010 migrations

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pos', '0010_add_contract_fields'),
        ('pos', '0010_gastocaja_and_more'),
    ]

    operations = [
        # No operations needed, just merge the branches
    ]
