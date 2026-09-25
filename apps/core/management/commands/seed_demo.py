"""
Load demonstration data: campuses, buildings, faculties, rooms, users and a
six-week booking diary (four weeks back, three ahead) with approvals, usage
history, audit entries and notifications.

    python manage.py seed_demo

Refuses to run when rooms already exist, so it never mixes with real data.
Every demo user signs in with DEMO_PASSWORD.
"""
import random
from contextlib import contextmanager
from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.approvals.models import ApprovalDecision, ApprovalStep
from apps.audit.models import AuditLog
from apps.bookings.models import PURPOSE_TO_TAG, Booking, BookingStatus
from apps.core.models import Building, Campus, Department, Faculty, Floor
from apps.notifications.models import Notification
from apps.rooms.models import (
    DraftStatus, Equipment, Room, RoomDraft, RoomStatus, RoomType, SuitabilityTag,
)
from apps.rooms.services import RoomStatusService
from apps.usage.models import UsageLog

DEMO_PASSWORD = "demo1234"

CAMPUSES = [("Main Campus", "MC"), ("College of Health Sciences", "CHS")]

# (campus code, name, code, floor levels)
BUILDINGS = [
    ("MC", "Great Hall", "GH", [0]),
    ("MC", "Science Block", "SCI", [0, 1, 2]),
    ("MC", "Engineering Building", "ENG", [0, 1, 2]),
    ("MC", "Commerce Building", "COM", [0, 1]),
    ("MC", "Education Building", "EDU", [0, 1]),
    ("MC", "Main Library", "LIB", [0, 1]),
    ("MC", "Administration Block", "ADM", [0, 1]),
    ("CHS", "Parirenyatwa Teaching Block", "PTB", [0, 1]),
]
FLOOR_NAMES = {0: "Ground", 1: "1st", 2: "2nd"}

# (name, code, is_administrative, [(department name, code), ...])
FACULTIES = [
    ("Faculty of Science", "SCI", False, [
        ("Computer Science", "CS"), ("Physics", "PHY"), ("Chemistry", "CHEM")]),
    ("Faculty of Engineering and the Built Environment", "FEBE", False, [
        ("Electrical Engineering", "EE"), ("Civil Engineering", "CIV")]),
    ("Faculty of Commerce", "COM", False, [
        ("Accountancy", "ACC"), ("Business Studies", "BUS")]),
    ("Faculty of Education", "EDU", False, [("Teacher Education", "TED")]),
    ("Faculty of Medicine and Health Sciences", "FMHS", False, [
        ("Nursing Science", "NUR"), ("Anatomy", "ANA")]),
    ("Central Administration", "CADM", True, [
        ("Examinations Office", "EXAM"), ("Estates and Works", "EST"), ("Library Services", "LIBS")]),
]

ROOM_TYPES = [
    ("Lecture Theatre", "LT"), ("Seminar Room", "SEM"), ("Laboratory", "LAB"),
    ("Computer Laboratory", "CLAB"), ("Hall", "HALL"), ("Boardroom", "BR"),
]

EQUIPMENT = ["Projector", "Smart board", "PA system", "Air conditioning",
             "Computers", "Whiteboard", "Video conferencing", "Fume cupboards"]

# Tags and equipment each room type gets by default.
TYPE_PROFILE = {
    "LT": (["Lectures", "Examinations", "Workshops"], ["Projector", "PA system", "Whiteboard"]),
    "SEM": (["Lectures", "Meetings", "Workshops"], ["Projector", "Whiteboard"]),
    "LAB": (["Lectures", "Workshops"], ["Whiteboard", "Fume cupboards"]),
    "CLAB": (["Lectures", "Workshops", "Examinations"], ["Computers", "Projector", "Air conditioning"]),
    "HALL": (["Examinations", "Events", "Conferences", "Lectures"], ["PA system", "Projector"]),
    "BR": (["Meetings", "Conferences"], ["Video conferencing", "Projector", "Air conditioning"]),
}

# (building, level, department code, type, name, capacity, condition, accessibility)
ROOMS = [
    ("GH", 0, "EXAM", "HALL", "Great Hall", 1200, "Good", "Wheelchair accessible"),
    ("ADM", 1, "EXAM", "HALL", "Examinations Hall A", 400, "Good", "Wheelchair accessible"),
    ("ADM", 1, "EST", "BR", "Senate Boardroom", 40, "Excellent", "Lift access"),
    ("ADM", 0, "EST", "SEM", "Admin Seminar Room", 35, "Good", "Wheelchair accessible"),
    ("LIB", 1, "LIBS", "SEM", "Library Seminar Room 1", 30, "Good", "Lift access"),
    ("LIB", 0, "LIBS", "CLAB", "Library E-Learning Centre", 80, "Good", "Wheelchair accessible"),
    ("SCI", 0, "CS", "LT", "Science Lecture Theatre 1", 250, "Good", "Wheelchair accessible"),
    ("SCI", 1, "CS", "CLAB", "Computer Lab 1", 60, "Good", "Lift access"),
    ("SCI", 1, "CS", "CLAB", "Computer Lab 2", 45, "Fair", "Lift access"),
    ("SCI", 2, "PHY", "LAB", "Physics Laboratory", 40, "Fair", "Stairs only"),
    ("SCI", 2, "CHEM", "LAB", "Chemistry Laboratory", 36, "Good", "Stairs only"),
    ("SCI", 0, "PHY", "SEM", "Physics Seminar Room", 25, "Good", "Wheelchair accessible"),
    ("ENG", 0, "EE", "LT", "Engineering Lecture Theatre", 180, "Good", "Wheelchair accessible"),
    ("ENG", 1, "EE", "LAB", "Electrical Machines Lab", 30, "Fair", "Lift access"),
    ("ENG", 2, "CIV", "LAB", "Materials Testing Lab", 28, "Good", "Lift access"),
    ("ENG", 1, "CIV", "SEM", "Civil Design Studio", 50, "Good", "Lift access"),
    ("COM", 0, "ACC", "LT", "Commerce Lecture Theatre", 300, "Good", "Wheelchair accessible"),
    ("COM", 1, "BUS", "SEM", "Business Studies Seminar Room", 40, "Good", "Stairs only"),
    ("COM", 1, "ACC", "BR", "Commerce Boardroom", 20, "Excellent", "Stairs only"),
    ("EDU", 0, "TED", "LT", "Education Lecture Theatre", 150, "Fair", "Wheelchair accessible"),
    ("EDU", 1, "TED", "SEM", "Micro-teaching Room", 30, "Good", "Stairs only"),
    ("PTB", 0, "NUR", "LT", "Health Sciences Lecture Theatre", 220, "Good", "Wheelchair accessible"),
    ("PTB", 1, "ANA", "LAB", "Anatomy Dissection Lab", 50, "Good", "Lift access"),
    ("PTB", 1, "NUR", "SEM", "Clinical Skills Room", 25, "Good", "Lift access"),
]

# Rooms held out of use for the demo: name -> (status, remark)
MANUAL_STATUS = {
    "Physics Laboratory": (RoomStatus.MAINTENANCE, "Gas lines being serviced."),
    "Computer Lab 2": (RoomStatus.CLEANING, ""),
    "Education Lecture Theatre": (RoomStatus.CLOSED, "Roof repairs after storm damage."),
}

# (username, full name, email, role, department code or None)
USERS = [
    ("tmoyo", "Tendai Moyo", "tmoyo@uz.ac.zw", "central_admin", "EST"),
    ("rchikwanha", "Rudo Chikwanha", "rchikwanha@uz.ac.zw", "dept_admin", "CS"),
    ("fsibanda", "Farai Sibanda", "fsibanda@uz.ac.zw", "dept_admin", "EE"),
    ("nmutasa", "Nyasha Mutasa", "nmutasa@uz.ac.zw", "dept_admin", "ACC"),
    ("pmarufu", "Precious Marufu", "pmarufu@uz.ac.zw", "dept_admin", "NUR"),
    ("kndlovu", "Kudakwashe Ndlovu", "kndlovu@uz.ac.zw", "approver", "EXAM"),
    ("tgumbo", "Tatenda Gumbo", "tgumbo@uz.ac.zw", "dept_admin", "LIBS"),
    ("smakoni", "Dr Simbarashe Makoni", "smakoni@uz.ac.zw", "viewer", "PHY"),
    ("cnyathi", "Chipo Nyathi", "cnyathi@uz.ac.zw", "viewer", "BUS"),
    ("bmhlanga", "Prof Blessing Mhlanga", "bmhlanga@uz.ac.zw", "viewer", "TED"),
]

SLOTS = [(time(8), time(10)), (time(10), time(12)), (time(12), time(13)),
         (time(14), time(16)), (time(16), time(17, 30))]

REJECT_REASONS = ["Room required for examinations.", "Clashes with departmental timetable.",
                  "Attendance exceeds the room's capacity.", "Please book a smaller room."]


@contextmanager
def backdatable(*models):
    """Let bulk_create keep explicit values in auto_now_add fields (to backdate history)."""
    fields = [f for m in models for f in m._meta.fields if getattr(f, "auto_now_add", False)]
    for f in fields:
        f.auto_now_add = False
    try:
        yield
    finally:
        for f in fields:
            f.auto_now_add = True


class Command(BaseCommand):
    help = "Load demonstration rooms, users and bookings (refuses if rooms already exist)."

    def add_arguments(self, parser):
        parser.add_argument("--seed", type=int, default=2026, help="Random seed for repeatable data.")

    def handle(self, *args, seed, **options):
        if Room.objects.exists():
            raise CommandError("Rooms already exist; demo data is only loaded into an empty inventory.")
        self.rng = random.Random(seed)
        self.tz = timezone.get_current_timezone()
        with transaction.atomic():
            self._hierarchy()
            self._catalogue()
            self._users()
            self._rooms()
            self._drafts()
            with backdatable(Booking, ApprovalStep, UsageLog, AuditLog, Notification):
                self._bookings()
            self._manual_statuses()
        result = RoomStatusService.refresh_live_statuses()
        self.stdout.write(self.style.SUCCESS(
            f"Demo data loaded: {Room.objects.count()} rooms, {Booking.objects.count()} bookings, "
            f"{len(USERS)} users (password '{DEMO_PASSWORD}'); "
            f"{result['rooms_changed']} live statuses refreshed."
        ))

    # ── Structure ──────────────────────────────────────────────────────
    def _hierarchy(self):
        campuses = {code: Campus.objects.get_or_create(code=code, defaults={"name": name})[0]
                    for name, code in CAMPUSES}
        self.buildings, self.floors = {}, {}
        for campus_code, name, code, levels in BUILDINGS:
            b, _ = Building.objects.get_or_create(
                campus=campuses[campus_code], code=code, defaults={"name": name})
            self.buildings[code] = b
            for level in levels:
                self.floors[(code, level)] = Floor.objects.get_or_create(
                    building=b, level=level, defaults={"name": FLOOR_NAMES[level]})[0]
        self.departments = {}
        for name, code, admin, depts in FACULTIES:
            f, _ = Faculty.objects.get_or_create(
                code=code, defaults={"name": name, "is_administrative": admin})
            for dname, dcode in depts:
                self.departments[dcode] = Department.objects.get_or_create(
                    faculty=f, code=dcode, defaults={"name": dname})[0]

    def _catalogue(self):
        self.types = {code: RoomType.objects.get_or_create(code=code, defaults={"name": name})[0]
                      for name, code in ROOM_TYPES}
        self.tags = {t.name: t for t in SuitabilityTag.objects.all()}
        for name in PURPOSE_TO_TAG.values():
            if name not in self.tags:
                self.tags[name] = SuitabilityTag.objects.create(name=name)
        self.equipment = {n: Equipment.objects.get_or_create(name=n)[0] for n in EQUIPMENT}

    def _users(self):
        self.users = {}
        for username, full_name, email, role, dept in USERS:
            user = User.objects.filter(username__iexact=username).first()
            if user is None:
                user = User.objects.create_user(
                    username, DEMO_PASSWORD, full_name=full_name, email=email, role=role,
                    department=self.departments[dept] if dept else None,
                )
            self.users[username] = user
        self.admin = User.objects.filter(is_superuser=True).order_by("pk").first() or self.users["tmoyo"]
        self.approver_for = {}
        for user in self.users.values():
            if user.role in ("dept_admin", "approver") and user.department_id:
                self.approver_for[user.department_id] = user

    def _rooms(self):
        seq = {code: 100 for code in self.types}
        self.rooms = []
        for bcode, level, dcode, tcode, name, cap, condition, access in ROOMS:
            seq[tcode] += 1
            room = Room.objects.create(
                code=f"UZ-{tcode}-{seq[tcode]}", name=name,
                building=self.buildings[bcode], floor=self.floors[(bcode, level)],
                department=self.departments[dcode], room_type=self.types[tcode],
                capacity=cap, condition=condition, accessibility=access,
            )
            tags, kit = TYPE_PROFILE[tcode]
            room.suitability.set([self.tags[t] for t in tags])
            room.equipment.set([self.equipment[e] for e in kit])
            self.rooms.append(room)

    def _drafts(self):
        pending = [
            ("SCI", 2, "CHEM", "LAB", "Organic Chemistry Lab 2", 32, "New fit-out completed in August."),
            ("ENG", 2, "EE", "CLAB", "Power Systems Simulation Lab", 40, ""),
            ("COM", 0, "BUS", "SEM", "Entrepreneurship Hub", 45, "Converted from storage room."),
        ]
        for bcode, level, dcode, tcode, name, cap, remarks in pending:
            RoomDraft.objects.create(
                name=name, building=self.buildings[bcode], floor=self.floors[(bcode, level)],
                department=self.departments[dcode], room_type=self.types[tcode], capacity=cap,
                remarks=remarks, submitted_by=self.approver_for.get(self.departments[dcode].pk, self.admin),
            )
        RoomDraft.objects.create(
            name="Basement Store Room", building=self.buildings["EDU"], floor=self.floors[("EDU", 0)],
            department=self.departments["TED"], room_type=self.types["SEM"], capacity=15,
            remarks="No ventilation; not suitable for teaching.", status=DraftStatus.REJECTED,
            submitted_by=self.users["bmhlanga"], verified_by=self.admin, verified_at=timezone.now(),
        )

    # ── Diary ──────────────────────────────────────────────────────────
    def _at(self, day, t):
        return timezone.make_aware(datetime.combine(day, t), self.tz)

    def _bookings(self):
        rng = self.rng
        today = timezone.localdate()
        requesters = [u for u in self.users.values()]
        days = [today + timedelta(days=d) for d in range(-28, 22)
                if (today + timedelta(days=d)).weekday() < 5]

        # Purposes each room may be booked for, from its type's suitability tags.
        purposes_for = {room.pk: [p for p, tag in PURPOSE_TO_TAG.items()
                                  if tag in TYPE_PROFILE[room.room_type.code][0]]
                        for room in self.rooms}

        bookings = []
        for day in days:
            for room in self.rooms:
                if room.name in MANUAL_STATUS and day >= today:
                    continue
                busy = 0.45 if room.room_type.code in ("LT", "CLAB", "SEM") else 0.25
                purposes = purposes_for[room.pk]
                for start, end in SLOTS:
                    if rng.random() > busy:
                        continue
                    purpose = rng.choice(purposes)
                    requester = rng.choice(requesters)
                    bookings.append(Booking(
                        room=room, requester=requester, requester_name=requester.full_name,
                        requester_dept=requester.department.name if requester.department else "",
                        purpose=purpose, date=day, start_time=start, end_time=end,
                        attendance=max(5, int(room.capacity * rng.uniform(0.4, 0.95))),
                        status=self._status_for(day, today),
                        created_at=self._at(day - timedelta(days=rng.randint(3, 14)), time(rng.randint(8, 16))),
                    ))
        for b in bookings:
            if b.status in (BookingStatus.APPROVED, BookingStatus.COMPLETED):
                b.approved_by = self._decider(b.room).full_name
        Booking.objects.bulk_create(bookings, batch_size=500)
        self._history(bookings, today)

    def _status_for(self, day, today):
        r = self.rng.random()
        if day < today:
            return (BookingStatus.COMPLETED if r < 0.88 else
                    BookingStatus.REJECTED if r < 0.94 else BookingStatus.CANCELLED)
        if day == today:
            return BookingStatus.APPROVED if r < 0.85 else BookingStatus.PENDING
        return (BookingStatus.APPROVED if r < 0.6 else
                BookingStatus.PENDING if r < 0.93 else BookingStatus.REJECTED)

    def _decider(self, room):
        return self.approver_for.get(room.department_id, self.admin)

    def _history(self, bookings, today):
        """Approval steps, usage log, audit trail and notifications that match the diary."""
        rng = self.rng
        steps, usage, audit, notes = [], [], [], []
        for b in bookings:
            ref = f"BK-{b.pk} — {b.room.code}"
            audit.append(AuditLog(timestamp=b.created_at, user=b.requester, action="Booking submitted",
                                  target=ref, previous_value="-", new_value="Pending approval"))
            if b.status in (BookingStatus.PENDING, BookingStatus.CANCELLED):
                continue
            decided = b.created_at + timedelta(hours=rng.randint(2, 40))
            approved = b.status != BookingStatus.REJECTED
            decider = self._decider(b.room)
            steps.append(ApprovalStep(
                booking=b, routed_to_department=b.room.department, decided_by=decider, decided_at=decided,
                decision=ApprovalDecision.APPROVED if approved else ApprovalDecision.REJECTED,
                comment="" if approved else rng.choice(REJECT_REASONS),
            ))
            audit.append(AuditLog(
                timestamp=decided, user=decider, target=ref, previous_value="Pending approval",
                action="Booking approved" if approved else "Booking rejected",
                new_value="Approved" if approved else "Rejected",
            ))
            if b.requester and b.date >= today - timedelta(days=7):
                notes.append(Notification(
                    user=b.requester, created_at=decided, is_read=b.date < today,
                    message=f"Your booking BK-{b.pk} for {b.room.name} was "
                            f"{'approved' if approved else 'rejected'}.",
                ))
            if b.status == BookingStatus.COMPLETED:
                usage.append(UsageLog(room=b.room, status=RoomStatus.IN_USE, changed_by=decider,
                                      timestamp=self._at(b.date, b.start_time), note=b.get_purpose_display()))
                usage.append(UsageLog(room=b.room, status=RoomStatus.AVAILABLE, changed_by=decider,
                                      timestamp=self._at(b.date, b.end_time)))

        # A few maintenance spells in the past for realism.
        for room in rng.sample(self.rooms, 5):
            day = today - timedelta(days=rng.randint(5, 25))
            usage.append(UsageLog(room=room, status=RoomStatus.MAINTENANCE, changed_by=self.admin,
                                  timestamp=self._at(day, time(7, 30)), note="Scheduled maintenance"))
            usage.append(UsageLog(room=room, status=RoomStatus.AVAILABLE, changed_by=self.admin,
                                  timestamp=self._at(day, time(17, 45))))

        pending = sum(1 for b in bookings if b.status == BookingStatus.PENDING)
        notes.append(Notification(user=self.admin, created_at=timezone.now(),
                                  message=f"{pending} booking requests are awaiting approval."))
        notes.append(Notification(user=self.admin, created_at=timezone.now() - timedelta(hours=3),
                                  message="3 new room drafts have been submitted for verification."))

        ApprovalStep.objects.bulk_create(steps, batch_size=500)
        UsageLog.objects.bulk_create(usage, batch_size=500)
        AuditLog.objects.bulk_create(audit, batch_size=500)
        Notification.objects.bulk_create(notes, batch_size=500)

    def _manual_statuses(self):
        for room in self.rooms:
            if room.name in MANUAL_STATUS:
                status, remark = MANUAL_STATUS[room.name]
                room.status, room.remarks = status, remark
                room.save(update_fields=["status", "remarks", "updated_at"])
