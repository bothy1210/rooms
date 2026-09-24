from django.contrib import admin

from apps.rooms.models import Equipment, Room, RoomDraft, RoomType, SuitabilityTag


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "building", "department", "room_type", "capacity", "status"]
    list_filter = ["status", "room_type", "department__faculty", "building"]
    search_fields = ["code", "name", "building__name"]
    filter_horizontal = ["suitability", "equipment"]
    readonly_fields = ["code"]


@admin.register(RoomDraft)
class RoomDraftAdmin(admin.ModelAdmin):
    list_display = ["name", "department", "room_type", "capacity", "status", "submitted_by", "verified_by"]
    list_filter = ["status", "department__faculty"]
    search_fields = ["name"]


admin.site.register(RoomType)
admin.site.register(SuitabilityTag)
admin.site.register(Equipment)
