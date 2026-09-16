from rest_framework.routers import DefaultRouter

from .views_api import (
    ClassEnrollmentViewSet,
    DashboardViewSet,
    GymClassViewSet,
    MembershipViewSet,
    PackageViewSet,
    PaymentViewSet,
)

router = DefaultRouter()
router.register('packages', PackageViewSet, basename='gym-package')
router.register('memberships', MembershipViewSet, basename='gym-membership')
router.register('payments', PaymentViewSet, basename='gym-payment')
router.register('classes', GymClassViewSet, basename='gym-class')
router.register('class-enrollment', ClassEnrollmentViewSet, basename='gym-class-enrollment')
router.register('dashboard', DashboardViewSet, basename='gym-dashboard')

urlpatterns = router.urls
