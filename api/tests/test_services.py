from django.contrib.auth import get_user_model
from django.test import TestCase
from types import SimpleNamespace
from unittest.mock import patch

from api.models import ParkingLevel, ParkingRequest
from api.services import (
    InvalidParkingRequestState,
    InvalidParkingRequestQuantity,
    InsufficientParkingSpots,
    cancel_request,
    confirm_request,
)


class ParkingRequestServiceTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="parking-owner",
            password="test-password",
        )
        self.level = ParkingLevel.objects.create(name="Test level", available=3)

    def create_request(self, quantity=1):
        return ParkingRequest.objects.create(
            owner=self.owner,
            level=self.level,
            quantity=quantity,
            status=ParkingRequest.Status.DRAFT,
        )

    def test_confirm_decreases_stock_once(self):
        parking_request = self.create_request(quantity=2)

        confirmed = confirm_request(parking_request.pk, self.owner)
        self.level.refresh_from_db()

        self.assertEqual(confirmed.status, ParkingRequest.Status.CONFIRMED)
        self.assertEqual(self.level.available, 1)

    def test_confirm_twice_returns_conflict(self):
        parking_request = self.create_request()
        confirm_request(parking_request.pk, self.owner)

        with self.assertRaises(InvalidParkingRequestState):
            confirm_request(parking_request.pk, self.owner)

    def test_confirm_without_stock_is_rejected(self):
        parking_request = self.create_request(quantity=4)

        with self.assertRaises(InsufficientParkingSpots):
            confirm_request(parking_request.pk, self.owner)

    def test_draft_cancel_does_not_change_stock(self):
        parking_request = self.create_request(quantity=2)
        before = self.level.available

        cancelled = cancel_request(parking_request.pk, self.owner)
        self.level.refresh_from_db()

        self.assertEqual(cancelled.status, ParkingRequest.Status.CANCELLED)
        self.assertEqual(self.level.available, before)

    def test_confirm_then_cancel_returns_stock_exactly_once(self):
        parking_request = self.create_request(quantity=2)
        before = self.level.available
        confirm_request(parking_request.pk, self.owner)

        cancel_request(parking_request.pk, self.owner)
        self.level.refresh_from_db()
        self.assertEqual(self.level.available, before)

        with self.assertRaises(InvalidParkingRequestState):
            cancel_request(parking_request.pk, self.owner)

    def test_invalid_quantity_is_rejected_in_service(self):
        parking_request = self.create_request(quantity=1)
        damaged_request = SimpleNamespace(
            pk=parking_request.pk,
            level_id=self.level.pk,
            quantity=0,
            status=ParkingRequest.Status.DRAFT,
        )

        with patch(
            "api.services._locked_request",
            return_value=damaged_request,
        ):
            with self.assertRaises(InvalidParkingRequestQuantity):
                confirm_request(parking_request.pk, self.owner)
