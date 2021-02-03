# Generated by Django 3.1.5 on 2021-02-03 21:42

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Operator',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=100, null=True)),
                ('user', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='operator', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('external_id', models.CharField(max_length=100)),
                ('active', models.BooleanField(default=False)),
                ('archived', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='Resource',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('external_id', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='ResourceProvider',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='ResourceSpecification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=8)),
                ('resource', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='res_spec', to='cella.resource')),
            ],
        ),
        migrations.CreateModel(
            name='Specification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('product_id', models.CharField(max_length=50)),
                ('is_active', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='SpecificationCategory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('coefficient', models.DecimalField(decimal_places=2, max_digits=8)),
            ],
        ),
        migrations.CreateModel(
            name='SpecificationPrice',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.DecimalField(decimal_places=2, max_digits=8)),
                ('time_stamp', models.DateTimeField(auto_now=True)),
                ('verified', models.BooleanField(default=False)),
                ('specification', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cella.specification')),
            ],
        ),
        migrations.CreateModel(
            name='SpecificationAction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action_type', models.CharField(choices=[('CRT', 'Create'), ('DCT', 'Deactivate'), ('ACT', 'Activate'), ('STP', 'Set price'), ('UPF', 'Update fields')], max_length=3)),
                ('time_stamp', models.DateTimeField(auto_now_add=True)),
                ('operator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='specification_actions', to='cella.operator')),
                ('specification', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='specification_actions', to='cella.specification')),
            ],
        ),
        migrations.AddField(
            model_name='specification',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='specifications', to='cella.specificationcategory'),
        ),
        migrations.CreateModel(
            name='ResourceSpecificationAssembled',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=8)),
                ('res_spec', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cella.resourcespecification')),
            ],
        ),
        migrations.AddField(
            model_name='resourcespecification',
            name='specification',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='res_spec', to='cella.specification'),
        ),
        migrations.CreateModel(
            name='ResourceCost',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.DecimalField(decimal_places=2, max_digits=8)),
                ('time_stamp', models.DateTimeField(auto_now=True)),
                ('verified', models.BooleanField(default=False)),
                ('resource', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cella.resource')),
            ],
        ),
        migrations.CreateModel(
            name='ResourceAmount',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.DecimalField(decimal_places=2, max_digits=8)),
                ('time_stamp', models.DateTimeField(auto_now=True)),
                ('resource', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='amounts', to='cella.resource')),
            ],
        ),
        migrations.CreateModel(
            name='ResourceAction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action_type', models.CharField(choices=[('CRT', 'Create'), ('UPF', 'Update fields'), ('STC', 'Set cost'), ('STA', 'Set amount'), ('RSA', 'Rise amount'), ('DRA', 'Drop amount')], max_length=3)),
                ('message', models.CharField(blank=True, max_length=200, null=True)),
                ('time_stamp', models.DateTimeField(auto_now_add=True)),
                ('operator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='resource_actions', to='cella.operator')),
                ('resource', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='resource_actions', to='cella.resource')),
            ],
        ),
        migrations.AddField(
            model_name='resource',
            name='provider',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='resources', to='cella.resourceprovider'),
        ),
        migrations.CreateModel(
            name='OrderSpecification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.IntegerField()),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cella.order')),
                ('specification', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cella.specification')),
            ],
        ),
        migrations.CreateModel(
            name='OrderAction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action_type', models.CharField(choices=[('CRT', 'Create'), ('CFM', 'Confirm'), ('CNL', 'Cancel'), ('CSN', 'Confirm specification')], max_length=3)),
                ('time_stamp', models.DateTimeField(auto_now_add=True)),
                ('operator', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='order_actions', to='cella.operator')),
                ('order', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='order_actions', to='cella.specification')),
            ],
        ),
    ]
