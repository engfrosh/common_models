# Generated by Django 4.1 on 2022-08-18 00:42

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('common_models', '0019_puzzleverificationphoto_puzzle_require_photo_upload'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='puzzle',
            unique_together={('order', 'stream')},
        ),
        migrations.AlterUniqueTogether(
            name='teampuzzleactivity',
            unique_together={('team', 'puzzle')},
        ),
    ]
