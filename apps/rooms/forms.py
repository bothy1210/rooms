"""Room registration and status forms."""
import re

from django import forms
from django.db import transaction
from django.db.models import Q

from apps.core.forms import new_code, typed_input
from apps.core.models import Building, Campus, Department, Faculty, Floor
from apps.rooms.models import RoomDraft, RoomStatus, RoomType

FLOOR_WORDS = {"ground": 0, "g": 0, "gf": 0, "basement": -1, "lower ground": -1, "lg": -1}

PHOTO_TYPES = ("image/jpeg", "image/png", "image/webp")
PHOTO_MAX_BYTES = 5 * 1024 * 1024


def _clean_name(value):
    return " ".join((value or "").split())


def _floor_level(name):
    """Level for a typed floor name: "Ground" -> 0, "1st" / "Level 1" / "1" -> 1, "Basement" -> -1."""
    lowered = name.lower().removesuffix(" floor")
    if lowered in FLOOR_WORDS:
        return FLOOR_WORDS[lowered]
    digits = re.search(r"-?\d+", lowered)
    return int(digits.group()) if digits else None


class RoomDraftForm(forms.ModelForm):
    """Department submits a proposed room (enters as a Draft).

    Building, floor, room type and department are typed, not picked. A typed
    name is matched to an existing record by name or code, ignoring case; one
    that does not exist yet is added when the draft is submitted.
    """

    building_name = forms.CharField(label="Building", max_length=150,
                                    widget=typed_input("e.g. Science Block", "building-options"))
    floor_name = forms.CharField(label="Floor", max_length=30,
                                 widget=typed_input("e.g. Ground, 1st, 2", "floor-options"))
    room_type_name = forms.CharField(label="Room type", max_length=60,
                                     widget=typed_input("e.g. Lecture Theatre", "room-type-options"))
    department_name = forms.CharField(label="Owning department / office", max_length=150,
                                      widget=typed_input("e.g. Computer Science", "department-options"))
    faculty_name = forms.CharField(label="Faculty", max_length=150, required=False,
                                   widget=typed_input("e.g. Faculty of Science", "faculty-options"))

    class Meta:
        model = RoomDraft
        fields = ["name", "capacity", "accessibility", "remarks", "photo"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. GIS Postgraduate Lab"}),
            "capacity": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "accessibility": forms.TextInput(attrs={"class": "form-control"}),
            "remarks": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "photo": forms.ClearableFileInput(attrs={"class": "form-control",
                                                     "accept": ",".join(PHOTO_TYPES)}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Suggestions while typing; any other name is still accepted.
        self.building_options = list(Building.objects.values_list("name", flat=True))
        self.floor_options = sorted(set(Floor.objects.values_list("name", flat=True)))
        self.room_type_options = list(RoomType.objects.values_list("name", flat=True))
        self.department_options = sorted(set(Department.objects.values_list("name", flat=True)))
        self.faculty_options = list(Faculty.objects.values_list("name", flat=True))
        self._resolved = {}

    def clean_capacity(self):
        cap = self.cleaned_data["capacity"]
        if cap < 1:
            raise forms.ValidationError("Capacity must be at least 1.")
        return cap

    def clean_photo(self):
        """Django checks the file really is an image; this bounds type and size."""
        photo = self.cleaned_data.get("photo")
        if not photo or not hasattr(photo, "content_type"):   # unchanged / already stored
            return photo
        if photo.content_type not in PHOTO_TYPES:
            raise forms.ValidationError("Use a JPEG, PNG or WebP image.")
        if photo.size > PHOTO_MAX_BYTES:
            raise forms.ValidationError(f"The photo must be under {PHOTO_MAX_BYTES // (1024 * 1024)} MB "
                                        f"(this one is {photo.size / (1024 * 1024):.1f} MB).")
        return photo

    def clean(self):
        cleaned = super().clean()
        building = self._resolve_building(_clean_name(cleaned.get("building_name")))
        self._resolved = {
            "building": building,
            "floor": self._resolve_floor(building, _clean_name(cleaned.get("floor_name"))),
            "room_type": self._resolve_room_type(_clean_name(cleaned.get("room_type_name"))),
            "department": self._resolve_department(_clean_name(cleaned.get("department_name")),
                                                   _clean_name(cleaned.get("faculty_name"))),
        }
        return cleaned

    # -- typed name -> record (unsaved if it is new) --
    @staticmethod
    def _resolve_building(name):
        if not name:
            return None
        return (Building.objects.filter(Q(name__iexact=name) | Q(code__iexact=name)).first()
                or Building(name=name))

    def _resolve_floor(self, building, name):
        if not (building and name):
            return None
        if building.pk:
            found = building.floors.filter(name__iexact=name).first()
            if found:
                return found
        level = _floor_level(name)
        if level is None:
            self.add_error("floor_name", "Type a floor the system can place, e.g. Ground, 1st, 2 or Basement.")
            return None
        if building.pk:
            found = building.floors.filter(level=level).first()
            if found:   # "1" or "Level 1" for a floor already set up as "1st"
                return found
        return Floor(name=name, level=level)

    @staticmethod
    def _resolve_room_type(name):
        if not name:
            return None
        return (RoomType.objects.filter(Q(name__iexact=name) | Q(code__iexact=name)).first()
                or RoomType(name=name))

    def _resolve_department(self, dept_name, fac_name):
        if not dept_name:
            return None
        faculty = None
        if fac_name:
            faculty = (Faculty.objects.filter(Q(name__iexact=fac_name) | Q(code__iexact=fac_name)).first()
                       or Faculty(name=fac_name))
        found = Department.objects.filter(Q(name__iexact=dept_name) | Q(code__iexact=dept_name))
        if faculty is not None:
            found = found.filter(faculty=faculty) if faculty.pk else found.none()
        found = list(found.select_related("faculty")[:2])
        if len(found) > 1:
            self.add_error("faculty_name", f"More than one faculty has a department called "
                                           f"“{dept_name}” — type the faculty too.")
            return None
        if found:
            return found[0]
        if faculty is None:
            self.add_error("faculty_name", f"There is no department called “{dept_name}” yet. "
                                           f"Type its faculty and it will be added under it.")
            return None
        return Department(name=dept_name, faculty=faculty)

    @transaction.atomic
    def draft_fields(self):
        """Keyword arguments for RoomRegistrationService.submit_draft, first adding
        any building, floor, room type or department that was typed in new."""
        building, floor = self._resolved["building"], self._resolved["floor"]
        room_type, department = self._resolved["room_type"], self._resolved["department"]
        if not building.pk:
            building.campus = Campus.objects.first() or Campus.objects.create(name="Main Campus", code="MC")
            building.code = new_code(Building, building.name, max_length=12, campus=building.campus)
            building.save()
        if not floor.pk:
            floor.building = building
            floor.save()
        if not room_type.pk:
            room_type.code = new_code(RoomType, room_type.name, max_length=8)
            room_type.save()
        if not department.pk:
            faculty = department.faculty
            if not faculty.pk:
                faculty.code = new_code(Faculty, faculty.name, max_length=12)
                faculty.save()
                department.faculty = faculty
            department.code = new_code(Department, department.name, max_length=12, faculty=faculty)
            department.save()
        data = {k: self.cleaned_data[k] for k in ("name", "capacity", "accessibility", "remarks", "photo")}
        return {**data, "building": building, "floor": floor, "room_type": room_type, "department": department}


class StatusUpdateForm(forms.Form):
    status = forms.ChoiceField(choices=RoomStatus.choices, widget=forms.Select(attrs={"class": "form-select"}))
