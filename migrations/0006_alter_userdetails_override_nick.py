# Generated by Django 4.1 on 2023-02-10 17:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common_models', '0005_discordmessage_pronounoption_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userdetails',
            name='override_nick',
            field=models.CharField(default=None, max_length=64, verbose_name='Name Override'),
        ),
    ]
