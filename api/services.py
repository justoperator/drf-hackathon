"""Atomic state transitions for parking requests."""
from django.db import transaction
from django.db.models import F

from .models import ParkingLevel, ParkingRequest


class ParkingRequestServiceError(Exception):
    """Base class for expected service-level failures."""


class ParkingRequestNotFound(ParkingRequestServiceError):
    pass


class InvalidParkingRequestState(ParkingRequestServiceError):
    pass


class InsufficientParkingSpots(ParkingRequestServiceError):
    pass


def _locked_request(request_id, user):
    try:
        return (
            ParkingRequest.objects.select_for_update()
            .select_related("level")
            .get(pk=request_id, owner=user)
        )
    except ParkingRequest.DoesNotExist as exc:
        raise ParkingRequestNotFound from exc


def confirm_request(request_id, user):
    with transaction.atomic():
        parking_request = _locked_request(request_id, user)
        if parking_request.status != ParkingRequest.Status.DRAFT:
            raise InvalidParkingRequestState

        updated = ParkingLevel.objects.filter(
            pk=parking_request.level_id,
            available__gte=parking_request.quantity,
        ).update(available=F("available") - parking_request.quantity)
        if updated != 1:
            raise InsufficientParkingSpots

        changed = ParkingRequest.objects.filter(
            pk=parking_request.pk,
            status=ParkingRequest.Status.DRAFT,
        ).update(status=ParkingRequest.Status.CONFIRMED)
        if changed != 1:
            raise InvalidParkingRequestState

        return ParkingRequest.objects.get(pk=parking_request.pk)


def cancel_request(request_id, user):
    with transaction.atomic():
        parking_request = _locked_request(request_id, user)
        if parking_request.status == ParkingRequest.Status.DRAFT:
            ParkingRequest.objects.filter(
                pk=parking_request.pk,
                status=ParkingRequest.Status.DRAFT,
            ).update(status=ParkingRequest.Status.CANCELLED)
        elif parking_request.status == ParkingRequest.Status.CONFIRMED:
            updated = ParkingLevel.objects.filter(pk=parking_request.level_id).update(
                available=F("available") + parking_request.quantity
            )
            if updated != 1:
                raise ParkingRequestNotFound
            changed = ParkingRequest.objects.filter(
                pk=parking_request.pk,
                status=ParkingRequest.Status.CONFIRMED,
            ).update(status=ParkingRequest.Status.CANCELLED)
            if changed != 1:
                raise InvalidParkingRequestState
        else:
            raise InvalidParkingRequestState

        return ParkingRequest.objects.get(pk=parking_request.pk)
