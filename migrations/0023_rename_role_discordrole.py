# Generated by Django 4.1 on 2022-08-26 04:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('common_models', '0022_puzzle_qr_code'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Role',
            new_name='DiscordRole',
        ),
    ]
