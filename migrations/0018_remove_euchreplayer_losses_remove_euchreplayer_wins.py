# Generated by Django 4.1 on 2023-01-04 23:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('common_models', '0017_euchreteam_points'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='euchreplayer',
            name='losses',
        ),
        migrations.RemoveField(
            model_name='euchreplayer',
            name='wins',
        ),
    ]
