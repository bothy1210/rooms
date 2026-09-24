"""
Core hierarchy models.

The system models a room in TWO independent structures — this separation is the
backbone of the whole design (see ARCHITECTURE.md §2):

    Physical hierarchy      Campus → Building → Floor → (Room)
        → drives room codes and location-based search/navigation

    Organisational hierarchy   Faculty → Department → (Room)
        → drives permissions, scoped dashboards and approval routing

Rooms owned by central offices (Great Hall, exam halls) simply sit under a
faculty flagged as an administrative/central unit.
"""
from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base: created/updated timestamps for every record."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ── Physical hierarchy ─────────────────────────────────────────────────
class Campus(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(
        max_length=8, unique=True, help_text="Short code used in room codes, e.g. MC (Main Campus)."
    )

    class Meta:
        verbose_name_plural = "campuses"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Building(TimeStampedModel):
    campus = models.ForeignKey(Campus, on_delete=models.PROTECT, related_name="buildings")
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=12, help_text="Short code used in room codes, e.g. SCI.")

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["campus", "code"], name="uniq_building_code_per_campus")
        ]

    def __str__(self):
        return f"{self.name} ({self.campus.code})"


class Floor(TimeStampedModel):
    """A floor within a building. `level` is used in room codes (0 = ground)."""

    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="floors")
    name = models.CharField(max_length=30, help_text="e.g. Ground, 1st, 2nd.")
    level = models.SmallIntegerField(help_text="Numeric level for sorting/codes; 0 = ground.")

    class Meta:
        ordering = ["building", "level"]
        constraints = [
            models.UniqueConstraint(fields=["building", "level"], name="uniq_floor_level_per_building")
        ]

    def __str__(self):
        return f"{self.building.name} — {self.name}"


# ── Organisational hierarchy ───────────────────────────────────────────
class Faculty(TimeStampedModel):
    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=12, unique=True)
    # Central admin / library / examinations are modelled as faculties flagged
    # "administrative" so university-level rooms fit the same tree.
    is_administrative = models.BooleanField(
        default=False, help_text="True for central offices (Administration, Examinations, Library)."
    )

    class Meta:
        verbose_name_plural = "faculties"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Department(TimeStampedModel):
    faculty = models.ForeignKey(Faculty, on_delete=models.PROTECT, related_name="departments")
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=12)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["faculty", "code"], name="uniq_department_code_per_faculty")
        ]

    def __str__(self):
        return f"{self.name} — {self.faculty.name}"
