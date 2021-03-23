# Generated by Django 3.1.5 on 2021-03-14 16:37


from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('specification', '0001_initial'),
        ('cella', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('external_id', models.CharField(max_length=100)),
                ('status', models.CharField(choices=[('INC', 'Inactive'), ('ACT', 'Active'), ('ASS', 'Assembling'), ('RDY', 'Ready'), ('ARC', 'Archived'), ('CNF', 'Confirmed'), ('CND', 'Canceled')], default='INC', max_length=3)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='OrderSource',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='OrderSpecification',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.IntegerField()),
                ('assembled', models.BooleanField(default=False)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='order_specification', to='order.order')),
                ('specification', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='order_specification', to='specification.specification')),
            ],
        ),
        migrations.AddField(
            model_name='order',
            name='source',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='order.ordersource'),
        ),
    ]
