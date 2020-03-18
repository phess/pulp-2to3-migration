# Generated by Django 2.2.11 on 2020-03-20 13:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pulp_2to3_migration', '0005_pulp2modulemd_pulp2modulemddefaults'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='pulp2lazycatalog',
            index=models.Index(fields=['pulp2_unit_id'], name='pulp_2to3_m_pulp2_u_c60485_idx'),
        ),
        migrations.AddIndex(
            model_name='pulp2lazycatalog',
            index=models.Index(fields=['pulp2_content_type_id'], name='pulp_2to3_m_pulp2_c_766098_idx'),
        ),
    ]
