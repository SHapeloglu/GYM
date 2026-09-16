from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models as m
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .gym import Gym

class Package(m.Model):
    class PackageType(m.TextChoices):
        MONTHLY = 'monthly', _('Monthly')
        YEARLY = 'yearly', _('Yearly')
        FREEZE = 'freeze', _('Freeze')
    class Meta:
        ordering = ['price']
    gym = m.ForeignKey(Gym, on_delete=m.CASCADE, related_name='packages')
    name = m.CharField(max_length=100)
    package_type = m.CharField(max_length=20, choices=PackageType.choices, default=PackageType.MONTHLY)
    price = m.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    duration_days = m.PositiveIntegerField()
    features = m.JSONField(default=dict, blank=True)
    is_active = m.BooleanField(default=True)
    created_at = m.DateTimeField(auto_now_add=True)
    updated_at = m.DateTimeField(auto_now=True)
    def __str__(self):
        return f'{self.name}'

class Membership(m.Model):
    class Status(m.TextChoices):
        ACTIVE = 'active', _('Active')
        EXPIRED = 'expired', _('Expired')
        FROZEN = 'frozen', _('Frozen')
        CANCELLED = 'cancelled', _('Cancelled')
    class Meta:
        ordering = ['-created_at']
    gym = m.ForeignKey(Gym, on_delete=m.CASCADE, related_name='memberships')
    user = m.ForeignKey(User, on_delete=m.CASCADE, related_name='gym_memberships')
    package = m.ForeignKey(Package, on_delete=m.PROTECT, related_name='memberships')
    start_date = m.DateField()
    end_date = m.DateField()
    status = m.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    frozen_until = m.DateField(blank=True, null=True)
    created_at = m.DateTimeField(auto_now_add=True)
    updated_at = m.DateTimeField(auto_now=True)
    def __str__(self):
        return f'{self.user} - {self.package.name}'
    @property
    def is_currently_active(self):
        today = timezone.now().date()
        return self.status == self.Status.ACTIVE and self.start_date <= today <= self.end_date

class Payment(m.Model):
    class Method(m.TextChoices):
        IYZICO = 'iyzico', _('iyzico')
        CASH = 'cash', _('Cash')
    class Status(m.TextChoices):
        PENDING = 'pending', _('Pending')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        REFUNDED = 'refunded', _('Refunded')
    class Meta:
        ordering = ['-created_at']
    membership = m.ForeignKey(Membership, on_delete=m.CASCADE, related_name='payments')
    amount = m.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    payment_method = m.CharField(max_length=20, choices=Method.choices, default=Method.IYZICO)
    status = m.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    transaction_id = m.CharField(max_length=100, blank=True, null=True, unique=True)
    raw_response = m.JSONField(blank=True, null=True)
    note = m.TextField(blank=True, null=True)
    created_at = m.DateTimeField(auto_now_add=True)
    updated_at = m.DateTimeField(auto_now=True)
    def __str__(self):
        return f'{self.membership} - {self.amount}\u20ba'

class GymClass(m.Model):
    class Meta:
        ordering = ['name']
    gym = m.ForeignKey(Gym, on_delete=m.CASCADE, related_name='classes')
    name = m.CharField(max_length=100)
    trainer = m.ForeignKey(User, on_delete=m.SET_NULL, null=True, blank=True, related_name='trainer_classes')
    schedule = m.JSONField(default=dict, blank=True)
    capacity = m.PositiveIntegerField(default=20)
    description = m.TextField(blank=True, null=True)
    is_active = m.BooleanField(default=True)
    created_at = m.DateTimeField(auto_now_add=True)
    updated_at = m.DateTimeField(auto_now=True)
    def __str__(self):
        return self.name
    @property
    def available_slots(self):
        enrolled = self.enrollments.filter(cancelled=False).count()
        return max(self.capacity - enrolled, 0)

class ClassEnrollment(m.Model):
    class Meta:
        ordering = ['-enrolled_at']
        unique_together = ('gym_class', 'user')
    gym_class = m.ForeignKey(GymClass, on_delete=m.CASCADE, related_name='enrollments')
    user = m.ForeignKey(User, on_delete=m.CASCADE, related_name='class_enrollments')
    attended = m.BooleanField(default=False)
    cancelled = m.BooleanField(default=False)
    enrolled_at = m.DateTimeField(auto_now_add=True)
    updated_at = m.DateTimeField(auto_now=True)
    def __str__(self):
        return f'{self.user.username} -> {self.gym_class.name}'
