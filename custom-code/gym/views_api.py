from django.db.models import Sum
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import ClassEnrollment, GymClass, Membership, Package, Payment
from .services import PaymentService, PaymentServiceError
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

    @action(detail=False, methods=['post'])
    def checkout(self, request):
        """
        POST /api/v2/gym/payments/checkout/
        Body: {"membership": <id>}

        Verilen membership icin iyzico checkout baslatir. IYZICO_API_KEY
        tanimli degilse PaymentService otomatik mock modda calisir (bkz.
        services.py). Basarili yanitta 'payment' (Payment kaydinin id/status'u)
        ve 'checkout' (iyzico'nun checkoutFormContent/paymentPageUrl/token
        alanlari) doner.
        """
        membership_id = request.data.get('membership')
        if not membership_id:
            return Response(
                {'membership': ['Bu alan zorunludur.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            membership = Membership.objects.get(id=membership_id)
        except Membership.DoesNotExist:
            return Response(
                {'membership': ['Boyle bir membership bulunamadi.']},
                status=status.HTTP_404_NOT_FOUND,
            )

        user = request.user
        if not user.is_staff and membership.user_id != user.id:
            return Response(
                {'detail': 'Bu membership size ait degil.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            payment, checkout_info = PaymentService.create_checkout(membership)
        except PaymentServiceError as exc:
            return Response(
                {'detail': str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                'payment': {'id': payment.id, 'status': payment.status, 'amount': str(payment.amount)},
                'checkout': checkout_info,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def webhook(self, request):
        """
        POST /api/v2/gym/payments/webhook/

        iyzico'dan gelen server-to-server webhook bildirimini isler.
        AllowAny: iyzico bizim auth token'imizi bilmiyor, guvenlik
        X-IYZ-SIGNATURE-V3 header imza dogrulamasiyla saglanir (bkz.
        PaymentService._verify_webhook_signature).

        iyzico 2xx disinda bir yanit alirsa 15 dakikada bir, 3 deneme
        boyunca tekrar gonderir. Bu yuzden dogrulama/eslesme hatalarinda
        bile 2xx donmek yerine gercek hata kodu donuyoruz — boylece iyzico
        tekrar dener ve gecici bir DB/agac hatasi kaybolmaz.
        """
        signature_header = request.headers.get('X-Iyz-Signature-V3') or request.headers.get('X-IYZ-SIGNATURE-V3')

        try:
            payment = PaymentService.handle_webhook(request.data, signature_header)
        except PaymentServiceError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'payment': {'id': payment.id, 'status': payment.status}}, status=status.HTTP_200_OK)

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
