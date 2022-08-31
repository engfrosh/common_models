# Generated by Django 4.1 on 2022-08-31 19:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common_models', '0024_alter_puzzle_order'),
    ]

    operations = [
        migrations.CreateModel(
            name='BooleanSetting',
            fields=[
                ('id', models.CharField(max_length=100, primary_key=True, serialize=False)),
                ('value', models.BooleanField(default=True)),
            ],
        ),
        migrations.AlterModelOptions(
            name='puzzleguess',
            options={'verbose_name': 'Puzzle Guess', 'verbose_name_plural': 'Puzzle Guesses'},
        ),
        migrations.AddField(
            model_name='team',
            name='scavenger_enabled_for_team',
            field=models.BooleanField(default=True),
        ),
    ]
