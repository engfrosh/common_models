# Generated by Django 4.1 on 2023-01-07 20:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common_models', '0020_alter_robertentry_user'),
    ]

    operations = [
        migrations.CreateModel(
            name='Announcement',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='Announcement ID')),
                ('created', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=200)),
                ('body', models.TextField()),
            ],
        ),
    ]
