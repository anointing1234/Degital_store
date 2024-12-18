# Generated by Django 5.0.7 on 2024-11-28 12:39

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Digital_shop', '0014_alter_background_slider_images_options'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Membership',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('course_name', models.CharField(choices=[('OGS', 'Organization Growth Strategies'), ('LS', 'Leadership'), ('PM', 'Principles of Ministry')], max_length=255)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('level_1', models.CharField(choices=[('OGS501', 'Level 1 - OGS501'), ('OGS502', 'Level 2 - OGS502'), ('LS501', 'Level 1 - LS501'), ('LS502', 'Level 2 - LS502'), ('PM501', 'Level 1 - PM501'), ('PM502', 'Level 2 - PM502')], max_length=20)),
                ('level_2', models.CharField(choices=[('OGS501', 'Level 1 - OGS501'), ('OGS502', 'Level 2 - OGS502'), ('LS501', 'Level 1 - LS501'), ('LS502', 'Level 2 - LS502'), ('PM501', 'Level 1 - PM501'), ('PM502', 'Level 2 - PM502')], max_length=20)),
                ('training_sections', models.IntegerField(default=2)),
                ('training_duration', models.CharField(default='45 mins for each section', max_length=100)),
                ('purchased_by', models.ManyToManyField(blank=True, related_name='memberships_purchased', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Membership',
                'verbose_name_plural': 'Memberships',
            },
        ),
    ]
