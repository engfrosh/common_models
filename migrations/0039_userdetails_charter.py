# Generated by Django 4.2.11 on 2024-03-12 18:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common_models', '0038_setting'),
    ]

    operations = [
        migrations.AddField(
            model_name='userdetails',
            name='charter',
            field=models.FileField(blank=True, null=True, upload_to='charter/'),
        ),
    ]
