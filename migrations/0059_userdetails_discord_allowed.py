# Generated by Django 4.1.13 on 2024-06-18 00:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common_models', '0058_rename_puzzle_file_is_link_puzzle_puzzle_is_link'),
    ]

    operations = [
        migrations.AddField(
            model_name='userdetails',
            name='discord_allowed',
            field=models.BooleanField(default=True, verbose_name='Discord Allowed'),
        ),
    ]
