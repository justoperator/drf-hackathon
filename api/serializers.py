"""Serializers for the public parking API."""
from rest_framework import serializers

from .models import ParkingLevel, ParkingRequest


class ParkingLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParkingLevel
        fields = ("id", "name", "available")
        read_only_fields = fields


class ParkingRequestSerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = ParkingRequest
        fields = ("id", "owner", "level", "quantity", "status")
        read_only_fields = ("id", "owner", "status")
