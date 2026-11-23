from django.contrib import admin

from .models import ParkingLevel, ParkingRequest


@admin.register(ParkingLevel)
class ParkingLevelAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "available")


@admin.register(ParkingRequest)
class ParkingRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "owner", "level", "quantity", "status")
    list_filter = ("status", "level")
