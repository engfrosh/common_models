# Generated by Django 4.1.7 on 2023-05-15 00:04

import common_models.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common_models', '0013_alter_discorduser_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='logo',
            field=models.FileField(blank=True, upload_to=common_models.models.logo_path),
        ),
        migrations.AlterField(
            model_name='discorduser',
            name='discord_username',
            field=models.CharField(blank=True, max_length=500),
        ),
    ]
