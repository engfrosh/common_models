# Generated by Django 4.2.14 on 2024-08-31 00:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common_models', '0077_rename_room_team__room_teamroom'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userdetails',
            name='shirt_size',
            field=models.CharField(blank=True, max_length=50, verbose_name='Shirt Size'),
        ),
        migrations.AlterField(
            model_name='userdetails',
            name='sweater_size',
            field=models.CharField(blank=True, max_length=50, verbose_name='Sweater Size'),
        ),
    ]
