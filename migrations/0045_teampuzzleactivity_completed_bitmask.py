# Generated by Django 4.2.11 on 2024-04-08 15:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common_models', '0044_alter_facilshift_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='teampuzzleactivity',
            name='completed_bitmask',
            field=models.IntegerField(default=0),
        ),
    ]
