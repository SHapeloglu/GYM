from django.contrib.auth.models import User
from rest_framework import serializers

from .models import ClassEnrollment, GymClass, Membership, Package, Payment
from .models.gym import Gym


class PackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Package
        fields = [
            'id', 'gym', 'name', 'package_type', 'price',
            'duration_days', 'features', 'is_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MembershipSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False
    )
    gym = serializers.PrimaryKeyRelatedField(
        queryset=Gym.objects.all(), required=False
    )
    user_username = serializers.CharField(source='user.username', read_only=True)
    gym_name = serializers.CharField(source='gym.name', read_only=True)
    package_detail = PackageSerializer(source='package', read_only=True)
    is_currently_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Membership
        fields = [
            'id', 'gym', 'gym_name', 'user', 'user_username',
            'package', 'package_detail', 'start_date', 'end_date',
            'status', 'frozen_until', 'is_currently_active',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        start_date = data.get('start_date', getattr(self.instance, 'start_date', None))
        end_date = data.get('end_date', getattr(self.instance, 'end_date', None))
        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError(
                {'end_date': 'end_date must be after start_date.'}
            )
        return data

    def create(self, validated_data):
        if not validated_data.get('gym'):
            package = validated_data.get('package')
            if package is not None:
                validated_data['gym'] = package.gym
        return super().create(validated_data)


class PaymentSerializer(serializers.ModelSerializer):
    membership_detail = MembershipSerializer(source='membership', read_only=True)
    amount_display = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'id', 'membership', 'membership_detail', 'amount', 'amount_display',
            'payment_method', 'status', 'transaction_id', 'raw_response', 'note',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'raw_response', 'created_at', 'updated_at']

    def get_amount_display(self, obj):
        return f'{obj.amount}\u20ba'


class GymClassSerializer(serializers.ModelSerializer):
    gym_name = serializers.CharField(source='gym.name', read_only=True)
    trainer_name = serializers.SerializerMethodField()
    enrolled_count = serializers.SerializerMethodField()
    available_slots = serializers.ReadOnlyField()

    class Meta:
        model = GymClass
        fields = [
            'id', 'gym', 'gym_name', 'name', 'trainer', 'trainer_name',
            'schedule', 'capacity', 'available_slots', 'enrolled_count',
            'description', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_trainer_name(self, obj):
        if not obj.trainer:
            return None
        return obj.trainer.get_full_name() or obj.trainer.username

    def get_enrolled_count(self, obj):
        return obj.enrollments.filter(cancelled=False).count()


class ClassEnrollmentSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False
    )
    user_username = serializers.CharField(source='user.username', read_only=True)
    gym_class_name = serializers.CharField(source='gym_class.name', read_only=True)

    class Meta:
        model = ClassEnrollment
        fields = [
            'id', 'gym_class', 'gym_class_name', 'user', 'user_username',
            'attended', 'cancelled', 'enrolled_at', 'updated_at',
        ]
        read_only_fields = ['id', 'enrolled_at', 'updated_at']
        # Disabled: DRF's auto UniqueTogetherValidator forces 'user' to be
        # required even when declared required=False, which breaks the
        # ViewSet's pattern of injecting the user in perform_create().
        # Uniqueness is enforced manually in validate() below instead.
        validators = []

    def validate(self, data):
        if self.instance is None:
            gym_class = data.get('gym_class')
            if gym_class is not None and gym_class.available_slots <= 0:
                raise serializers.ValidationError(
                    'Class capacity is full. Cannot enroll.'
                )
            request = self.context.get('request')
            user = data.get('user') or (
                getattr(request, 'user', None) if request else None
            )
            if user is not None and gym_class is not None:
                exists = ClassEnrollment.objects.filter(
                    gym_class=gym_class, user=user, cancelled=False
                ).exists()
                if exists:
                    raise serializers.ValidationError(
                        'User is already enrolled in this class.'
                    )
        return data
