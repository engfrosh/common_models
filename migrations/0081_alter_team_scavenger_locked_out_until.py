# Generated by Django 5.1.4 on 2025-02-16 17:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('common_models', '0080_calendar_rule_calendarrelation_event_eventrelation_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='team',
            name='scavenger_locked_out_until',
            field=models.BigIntegerField(default=0, verbose_name='Scavenger Locked Out Until'),
        ),
    ]
