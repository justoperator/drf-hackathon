"""ViewSets for the parking catalog and owner-scoped requests."""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets

from .models import ParkingLevel, ParkingRequest
from .permissions import IsParkingRequestOwner, ReadOnlyCatalogPermission
from .serializers import ParkingLevelSerializer, ParkingRequestSerializer
from .services import (
    InsufficientParkingSpots,
    InvalidParkingRequestState,
    ParkingRequestNotFound,
    cancel_request,
    confirm_request,
)


class ParkingLevelViewSet(viewsets.ModelViewSet):
    queryset = ParkingLevel.objects.all()
    serializer_class = ParkingLevelSerializer
    permission_classes = (ReadOnlyCatalogPermission,)
    http_method_names = ("get", "head", "options")


class ParkingRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ParkingRequestSerializer
    permission_classes = (IsParkingRequestOwner,)

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return ParkingRequest.objects.none()
        return ParkingRequest.objects.filter(owner=self.request.user).select_related("level")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def _ensure_editable(self, instance):
        if instance.status != ParkingRequest.Status.DRAFT:
            return Response(
                {"detail": "Заявку можна змінювати лише у стані draft."},
                status=status.HTTP_409_CONFLICT,
            )
        return None

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        error = self._ensure_editable(instance)
        if error:
            return error
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        error = self._ensure_editable(instance)
        if error:
            return error
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status in (
            ParkingRequest.Status.CONFIRMED,
            ParkingRequest.Status.CANCELLED,
        ):
            return Response(
                {"detail": "Підтверджені та скасовані заявки не можна видаляти."},
                status=status.HTTP_409_CONFLICT,
            )
        return super().destroy(request, *args, **kwargs)

    def _transition(self, request, transition):
        try:
            parking_request = transition(self.kwargs["pk"], request.user)
        except ParkingRequestNotFound:
            return Response(
                {"detail": "Заявку не знайдено."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except InsufficientParkingSpots:
            return Response(
                {"detail": "На рівні недостатньо вільних місць."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except InvalidParkingRequestState:
            return Response(
                {"detail": "Недозволений перехід стану заявки."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(self.get_serializer(parking_request).data)

    @action(detail=True, methods=("post",))
    def confirm(self, request, *args, **kwargs):
        return self._transition(request, confirm_request)

    @action(detail=True, methods=("post",))
    def cancel(self, request, *args, **kwargs):
        return self._transition(request, cancel_request)
