# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-04-22 10:23
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('conversations', '0003_post_conversation'),
    ]

    operations = [
        migrations.AlterField(
            model_name='post',
            name='conversation',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='posts', to='conversations.Conversation'),
        ),
    ]
