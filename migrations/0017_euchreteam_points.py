# Generated by Django 4.1 on 2023-01-04 10:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common_models', '0016_euchrecard_played'),
    ]

    operations = [
        migrations.AddField(
            model_name='euchreteam',
            name='points',
            field=models.IntegerField(default=0, verbose_name='Points'),
        ),
    ]
