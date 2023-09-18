# Generated by Django 4.2.1 on 2023-07-28 06:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxon_search', '0011_delete_ensembltaxonflat'),
    ]

    operations = [
        migrations.CreateModel(
            name='NCBITaxonFlat',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('taxon_id', models.IntegerField()),
                ('parent_id', models.IntegerField()),
                ('left_index', models.IntegerField(default=0)),
                ('right_index', models.IntegerField(default=0)),
                ('rank', models.CharField(db_index=True, max_length=32)),
                ('name', models.CharField(db_index=True, max_length=500)),
                ('name_class', models.CharField(db_index=True, max_length=50)),
                ('species_taxon_id', models.IntegerField()),
                ('name_index', models.CharField(db_index=True, max_length=500)),
            ],
            options={
                'db_table': 'ncbi_taxon_flat',
                'unique_together': {('taxon_id', 'name', 'name_class', 'species_taxon_id')},
            },
        ),
    ]