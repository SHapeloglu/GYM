import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gym', '0008_auto_20190618_1617'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='GymClass',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('schedule', models.JSONField(blank=True, default=dict)),
                ('capacity', models.PositiveIntegerField(default=20)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('gym', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='classes', to='gym.gym')),
                ('trainer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='trainer_classes', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Package',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('package_type', models.CharField(choices=[('monthly', 'Monthly'), ('yearly', 'Yearly'), ('freeze', 'Freeze')], default='monthly', max_length=20)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)])),
                ('duration_days', models.PositiveIntegerField()),
                ('features', models.JSONField(blank=True, default=dict)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('gym', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='packages', to='gym.gym')),
            ],
            options={
                'ordering': ['price'],
            },
        ),
        migrations.CreateModel(
            name='Membership',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('status', models.CharField(choices=[('active', 'Active'), ('expired', 'Expired'), ('frozen', 'Frozen'), ('cancelled', 'Cancelled')], default='active', max_length=20)),
                ('frozen_until', models.DateField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('gym', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='gym.gym')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='gym_memberships', to=settings.AUTH_USER_MODEL)),
                ('package', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='memberships', to='gym.package')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)])),
                ('payment_method', models.CharField(choices=[('iyzico', 'iyzico'), ('cash', 'Cash')], default='iyzico', max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed'), ('refunded', 'Refunded')], default='pending', max_length=20)),
                ('transaction_id', models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ('raw_response', models.JSONField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('membership', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='gym.membership')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ClassEnrollment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attended', models.BooleanField(default=False)),
                ('cancelled', models.BooleanField(default=False)),
                ('enrolled_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='class_enrollments', to=settings.AUTH_USER_MODEL)),
                ('gym_class', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='enrollments', to='gym.gymclass')),
            ],
            options={
                'ordering': ['-enrolled_at'],
                'unique_together': {('gym_class', 'user')},
            },
        ),
    ]
