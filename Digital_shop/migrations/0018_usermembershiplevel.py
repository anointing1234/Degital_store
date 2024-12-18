# Generated by Django 5.0.7 on 2024-11-29 13:37

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Digital_shop', '0017_remove_membership_training_duration'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserMembershipLevel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('level', models.CharField(choices=[('OGS501', 'Level 1 - OGS501'), ('OGS502', 'Level 2 - OGS502'), ('LS501', 'Level 1 - LS501'), ('LS502', 'Level 2 - LS502'), ('PM501', 'Level 1 - PM501'), ('PM502', 'Level 2 - PM502')], max_length=20)),
                ('training_sections', models.IntegerField(default=3)),
                ('purchased_at', models.DateTimeField(auto_now_add=True)),
                ('membership', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='Digital_shop.membership')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'User Membership Level',
                'verbose_name_plural': 'User Membership Levels',
                'unique_together': {('user', 'membership', 'level', 'training_sections')},
            },
        ),
    ]
