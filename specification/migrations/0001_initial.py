# Generated by Django 3.1.5 on 2021-03-03 03:41

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('cella', '0001_initial'),
        ('resources', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Specification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=400, null=True)),
                ('product_id', models.CharField(max_length=50)),
                ('is_active', models.BooleanField(default=True)),
                ('price', models.DecimalField(decimal_places=2, default=0.0, max_digits=12)),
                ('amount', models.IntegerField(default=0)),
                ('coefficient', models.DecimalField(decimal_places=2, default=None, max_digits=12, null=True)),
                ('verified', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('storage_place', models.CharField(max_length=100, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='SpecificationCategory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('coefficient', models.DecimalField(decimal_places=2, max_digits=12, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='SpecificationResource',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('resource', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='res_specs', to='resources.resource')),
                ('specification', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='res_specs', to='specification.specification')),
            ],
        ),
        migrations.CreateModel(
            name='SpecificationAction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action_type', models.CharField(choices=[('CRT', 'Create'), ('DCT', 'Deactivate'), ('ACT', 'Activate'), ('STP', 'Set price'), ('STA', 'Set amount'), ('UPF', 'Update fields'), ('SCT', 'Set coefficient'), ('SCY', 'Set category'), ('BLS', 'Build set')], max_length=3)),
                ('time_stamp', models.DateTimeField(auto_now_add=True)),
                ('value', models.CharField(max_length=300, null=True)),
                ('operator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='specification_actions', to='cella.operator')),
                ('specification', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='specification_actions', to='specification.specification')),
            ],
        ),
        migrations.AddField(
            model_name='specification',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='specifications', to='specification.specificationcategory'),
        ),
    ]
