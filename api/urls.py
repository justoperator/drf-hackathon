from rest_framework.routers import DefaultRouter

from .views import ParkingLevelViewSet, ParkingRequestViewSet

router = DefaultRouter()
router.register("levels", ParkingLevelViewSet, basename="parking-level")
router.register("parking-requests", ParkingRequestViewSet, basename="parking-request")

urlpatterns = router.urls
