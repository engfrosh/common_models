# Generated by Django 4.1 on 2023-02-05 02:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common_models', '0002_alter_userdetails_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='roleinvite',
            name='role',
            field=models.CharField(max_length=200, verbose_name='Role IDs'),
        ),
    ]
