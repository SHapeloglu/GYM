from django.db.models import Sum
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import ClassEnrollment, GymClass, Membership, Package, Payment
from .serializers import (
    ClassEnrollmentSerializer,
    GymClassSerializer,
    MembershipSerializer,
    PackageSerializer,
    PaymentSerializer,
)

class PackageViewSet(viewsets.ModelViewSet):
    queryset = Package.objects.all()
    serializer_class = PackageSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class MembershipViewSet(viewsets.ModelViewSet):
    serializer_class = MembershipSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Membership.objects.all()
        return Membership.objects.filter(user=user)
    def perform_create(self, serializer):
        user = self.request.user
        if user.is_staff and 'user' in self.request.data:
            serializer.save()
        else:
            serializer.save(user=user)

class PaymentViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Payment.objects.all()
        return Payment.objects.filter(membership__user=user)

class GymClassViewSet(viewsets.ModelViewSet):
    queryset = GymClass.objects.filter(is_active=True)
    serializer_class = GymClassSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class ClassEnrollmentViewSet(viewsets.ModelViewSet):
    serializer_class = ClassEnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return ClassEnrollment.objects.all()
        return ClassEnrollment.objects.filter(user=user)
    def perform_create(self, serializer):
        user = self.request.user
        if user.is_staff and 'user' in self.request.data:
            serializer.save()
        else:
            serializer.save(user=user)

class DashboardViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAdminUser]
    def list(self, request):
        today = timezone.now().date()
        month_start = today.replace(day=1)
        active_members = Membership.objects.filter(
            status=Membership.Status.ACTIVE, end_date__gte=today
        ).count()
        monthly_revenue = (
            Payment.objects.filter(
                status=Payment.Status.COMPLETED, created_at__date__gte=month_start
            ).aggregate(total=Sum('amount'))['total'] or 0
        )
        total_classes = GymClass.objects.filter(is_active=True).count()
        total_revenue = (
            Payment.objects.filter(
                status=Payment.Status.COMPLETED
            ).aggregate(total=Sum('amount'))['total'] or 0
        )
        return Response({
            'summary': {
                'active_members': active_members,
                'monthly_revenue': str(monthly_revenue),
                'total_classes': total_classes,
                'total_revenue': str(total_revenue),
            },
            'generated_at': timezone.now(),
        })
