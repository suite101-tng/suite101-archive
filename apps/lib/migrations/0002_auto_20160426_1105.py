# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-04-26 11:05
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import lib.models


class Migration(migrations.Migration):

    dependencies = [
        ('lib', '0001_initial'),
    ]

    operations = [
        migrations.DeleteModel(
            name='WeeklyDigestSend',
        ),
        migrations.RemoveField(
            model_name='genericimage',
            name='caption',
        ),
        migrations.RemoveField(
            model_name='genericimage',
            name='legacy_image_id',
        ),
        migrations.AddField(
            model_name='genericimage',
            name='image_large',
            field=models.ImageField(blank=True, null=True, upload_to=b'images/large'),
        ),
        migrations.AddField(
            model_name='genericimage',
            name='upload_url',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='genericimage',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to=lib.models.generic_images_file_name),
        ),
        migrations.AlterField(
            model_name='genericimage',
            name='image_small',
            field=models.ImageField(blank=True, null=True, upload_to=b'images/small'),
        ),
        migrations.AlterField(
            model_name='genericimage',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to=settings.AUTH_USER_MODEL),
        ),
    ]
