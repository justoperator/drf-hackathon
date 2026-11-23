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


class InvalidParkingRequestQuantity(ParkingRequestServiceError):
    pass


def _validate_quantity(quantity):
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
        raise InvalidParkingRequestQuantity


def _locked_request(request_id, user):
    try:
        return (
            ParkingRequest.objects.select_for_update()
            .select_related("level")
            .get(pk=request_id, owner=user)
        )
    except ParkingRequest.DoesNotExist as exc:
        raise ParkingRequestNotFound from exc


def _ensure_draft(parking_request):
    if parking_request.status != ParkingRequest.Status.DRAFT:
        raise InvalidParkingRequestState


def _reserve_spots(parking_request):
    changed = ParkingLevel.objects.filter(
        pk=parking_request.level_id,
        available__gte=parking_request.quantity,
    ).update(available=F("available") - parking_request.quantity)
    if changed != 1:
        raise InsufficientParkingSpots


def _mark_confirmed(parking_request):
    changed = ParkingRequest.objects.filter(
        pk=parking_request.pk,
        status=ParkingRequest.Status.DRAFT,
    ).update(status=ParkingRequest.Status.CONFIRMED)
    if changed != 1:
        raise InvalidParkingRequestState


def confirm_request(request_id, user):
    with transaction.atomic():
        parking_request = _locked_request(request_id, user)
        _validate_quantity(parking_request.quantity)
        _ensure_draft(parking_request)
        _reserve_spots(parking_request)
        _mark_confirmed(parking_request)
        return ParkingRequest.objects.get(pk=parking_request.pk)


def _cancel_draft(parking_request):
    changed = ParkingRequest.objects.filter(
        pk=parking_request.pk,
        status=ParkingRequest.Status.DRAFT,
    ).update(status=ParkingRequest.Status.CANCELLED)
    if changed != 1:
        raise InvalidParkingRequestState


def _return_confirmed_spots(parking_request):
    changed = ParkingLevel.objects.filter(pk=parking_request.level_id).update(
        available=F("available") + parking_request.quantity
    )
    if changed != 1:
        raise ParkingRequestNotFound

    changed = ParkingRequest.objects.filter(
        pk=parking_request.pk,
        status=ParkingRequest.Status.CONFIRMED,
    ).update(status=ParkingRequest.Status.CANCELLED)
    if changed != 1:
        raise InvalidParkingRequestState


def cancel_request(request_id, user):
    with transaction.atomic():
        parking_request = _locked_request(request_id, user)
        _validate_quantity(parking_request.quantity)
        if parking_request.status == ParkingRequest.Status.DRAFT:
            _cancel_draft(parking_request)
        elif parking_request.status == ParkingRequest.Status.CONFIRMED:
            _return_confirmed_spots(parking_request)
        else:
            raise InvalidParkingRequestState

        return ParkingRequest.objects.get(pk=parking_request.pk)
