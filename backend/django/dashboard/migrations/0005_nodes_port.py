# Generated by Django 3.0.1 on 2019-12-24 02:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0004_auto_20191220_1538'),
    ]

    operations = [
        migrations.AddField(
            model_name='nodes',
            name='port',
            field=models.IntegerField(default=0),
        ),
    ]
