# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-04-21 21:22
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('conversations', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='conversation',
            name='conversation_parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='child_conversations', to='conversations.Post'),
        ),
    ]
