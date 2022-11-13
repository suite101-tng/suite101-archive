# -*- coding: utf-8 -*-
# Generated by Django 1.9.4 on 2016-04-19 23:00
from __future__ import unicode_literals

import articles.models
import autoslug.fields
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Article',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(db_index=True, default=django.utils.timezone.now, editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False)),
                ('saved_on', models.DateTimeField(db_index=True, null=True)),
                ('slug', autoslug.fields.AutoSlugField(editable=True, max_length=100, populate_from=b'get_slug', unique=True)),
                ('title', models.CharField(blank=True, max_length=255)),
                ('subtitle', models.TextField(blank=True)),
                ('body', model_utils.fields.SplitField(blank=True, no_excerpt_field=True)),
                ('body_length', models.IntegerField(null=True)),
                ('word_count', models.IntegerField(default=0)),
                ('story_dup', models.BooleanField(default=False)),
                ('external_canonical', models.URLField(blank=True, verbose_name=b'Canonical')),
                ('alchemy_entity_str', models.TextField(blank=True)),
                ('alchemy_keyword_str', models.TextField(blank=True)),
                ('entity_list', models.TextField(blank=True)),
                ('keyword_list', models.TextField(blank=True)),
                ('tag_list', models.TextField(blank=True)),
                ('status', models.CharField(choices=[(b'draft', b'draft'), (b'published', b'published'), (b'deleted', b'deleted')], db_index=True, default=b'draft', max_length=20)),
                ('ads_override', models.CharField(choices=[(b'auto', b'auto'), (b'show', b'show'), (b'hide', b'hide')], default=b'auto', max_length=20)),
                ('featured', models.DateTimeField(db_index=True, null=True)),
                ('hashed_id', models.CharField(blank=True, db_index=True, max_length=50)),
                ('deferred', models.BooleanField(default=False)),
                ('archive', models.BooleanField(db_index=True, default=False)),
                ('_body_excerpt', models.TextField(editable=False)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='articles', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created'],
                'verbose_name_plural': 'Articles',
            },
        ),
        migrations.CreateModel(
            name='ArticleImage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(blank=True, null=True, upload_to=articles.models.article_images_file_name)),
                ('image_large', models.ImageField(blank=True, null=True, upload_to=b'article_images/large')),
                ('image_small', models.ImageField(blank=True, null=True, upload_to=b'article_images/small')),
                ('is_main_image', models.BooleanField(default=False)),
                ('upload_url', models.URLField(blank=True, null=True)),
                ('image_type', models.CharField(choices=[(b'normal', b'normal'), (b'lefty', b'lefty'), (b'righty', b'righty')], default=b'normal', max_length=10)),
                ('landscape', models.BooleanField(default=True)),
                ('caption', models.CharField(blank=True, max_length=512)),
                ('credit', models.CharField(blank=True, max_length=512)),
                ('credit_link', models.CharField(blank=True, max_length=512)),
                ('sort_order', models.IntegerField(default=0)),
                ('legacy_image_id', models.IntegerField(blank=True, null=True)),
                ('article', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='images', to='articles.Article')),
            ],
            options={
                'ordering': ['sort_order'],
            },
        ),
        migrations.CreateModel(
            name='StoryEmbed',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('object_id', models.PositiveIntegerField(null=True)),
                ('caption', models.CharField(blank=True, max_length=512)),
                ('cover', models.BooleanField(default=False)),
                ('spill', models.BooleanField(default=False)),
                ('content_type', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType')),
                ('story', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='embeds', to='articles.Article')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='StoryParent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('object_id', models.PositiveIntegerField(null=True)),
                ('content_type', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType')),
                ('story', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='story_parent', to='articles.Article')),
            ],
        ),
    ]