# Generated by Django 4.1 on 2023-02-10 18:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common_models', '0007_alter_userdetails_override_nick'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pronounoption',
            name='emote',
            field=models.CharField(max_length=64, verbose_name='Emote'),
        ),
    ]
