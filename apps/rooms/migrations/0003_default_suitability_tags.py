"""The suitability tags the booking purposes map to (see bookings.PURPOSE_TO_TAG).

Without these there is nothing to tag a room with, and tagging is how a room is
restricted to certain purposes. Rooms carrying no tags are unrestricted.
"""
from django.db import migrations

TAGS = ["Lectures", "Examinations", "Meetings", "Workshops", "Conferences", "Events"]


def add_tags(apps, schema_editor):
    SuitabilityTag = apps.get_model("rooms", "SuitabilityTag")
    for name in TAGS:
        SuitabilityTag.objects.get_or_create(name=name)


def remove_tags(apps, schema_editor):
    SuitabilityTag = apps.get_model("rooms", "SuitabilityTag")
    # Only drop the ones no room uses, so tagging work is never lost.
    SuitabilityTag.objects.filter(name__in=TAGS, rooms__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("rooms", "0002_roomdraft_photo"),
    ]

    operations = [
        migrations.RunPython(add_tags, remove_tags),
    ]
