from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LogSheetViewSet, DutyStatusChangeViewSet

router = DefaultRouter()
router.register(r'logs', LogSheetViewSet)
router.register(r'duty-status', DutyStatusChangeViewSet)

urlpatterns = [
    path('', include(router.urls)),
] 