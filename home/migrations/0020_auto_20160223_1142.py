# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0019_auto_20160223_1139'),
    ]

    operations = [
        migrations.AlterField(
            model_name='store',
            name='phone',
            field=models.CharField(max_length=15, validators=[django.core.validators.RegexValidator(regex='^[0-9]+(-?[0-9]+)+$', message='Please enter a valid phone number', code='invalid_phone')]),
        ),
    ]
