# Data Dictionary — UZ Room Inventory & Usage Monitoring System

Generated from the Django models. Each section lists a table, its purpose, and
its main fields. Standard `created_at` / `updated_at` timestamps are present on
most tables and omitted here for brevity.

---

## Core — hierarchy

### `core_campus`
Physical top level.

| Field | Type | Notes |
|---|---|---|
| name | varchar(120) | unique |
| code | varchar(8) | unique; used in room codes (e.g. MC) |

### `core_building`
| Field | Type | Notes |
|---|---|---|
| campus_id | FK → campus | |
| name | varchar(150) | |
| code | varchar(12) | unique per campus |

### `core_floor`
| Field | Type | Notes |
|---|---|---|
| building_id | FK → building | |
| name | varchar(30) | e.g. Ground, 1st |
| level | smallint | 0 = ground; unique per building |

### `core_faculty`
| Field | Type | Notes |
|---|---|---|
| name | varchar(150) | unique |
| code | varchar(12) | unique |
| is_administrative | bool | true for central offices (holds university-level rooms) |

### `core_department`
| Field | Type | Notes |
|---|---|---|
| faculty_id | FK → faculty | |
| name | varchar(150) | |
| code | varchar(12) | unique per faculty |

---

## Accounts

### `accounts_user`
| Field | Type | Notes |
|---|---|---|
| username | varchar(150) | unique ignoring case; login identifier (e.g. tmoyo) |
| full_name | varchar(150) | |
| email | email | optional |
| role | varchar(20) | central_admin / dept_admin / approver / viewer |
| department_id | FK → department | organisational scope |
| faculty_id | FK → faculty | backfilled from department |
| is_active, is_staff, is_superuser | bool | Django auth flags |

---

## Rooms

### `rooms_roomtype`
| Field | Type | Notes |
|---|---|---|
| name | varchar(60) | unique (Lecture room, Laboratory, Hall…) |
| code | varchar(8) | unique; used in room codes (LT, LAB, HALL) |

### `rooms_suitabilitytag`
| Field | Type | Notes |
|---|---|---|
| name | varchar(40) | unique (Lectures, Examinations, Events…) |

### `rooms_equipment`
| Field | Type | Notes |
|---|---|---|
| name | varchar(60) | unique |

### `rooms_room`
The official, bookable inventory record.

| Field | Type | Notes |
|---|---|---|
| code | varchar(30) | unique, immutable; issued at verification (UZ-LT-101) |
| name | varchar(150) | |
| building_id | FK → building | physical location |
| floor_id | FK → floor | physical location |
| department_id | FK → department | ownership → scope & approval routing |
| room_type_id | FK → room_type | physical classification |
| suitability | M2M → suitability_tag | what it can be used for |
| equipment | M2M → equipment | |
| capacity | int | |
| condition | varchar(20) | |
| accessibility | varchar(60) | |
| status | varchar(20) | available / in_use / booked / maintenance / cleaning / closed |
| photo | image | optional |
| remarks | text | |

### `rooms_roomdraft`
A proposed room awaiting verification (not bookable).

| Field | Type | Notes |
|---|---|---|
| name, building_id, floor_id, department_id, room_type_id, capacity | — | as submitted |
| status | varchar(10) | draft / verified / rejected |
| submitted_by_id | FK → user | |
| verified_by_id | FK → user | set at verification |
| verified_at | datetime | |
| resulting_room_id | FK → room | the room this draft became |

---

## Bookings

### `bookings_booking`
| Field | Type | Notes |
|---|---|---|
| room_id | FK → room | |
| requester_id | FK → user | |
| requester_name | varchar(150) | |
| requester_dept | varchar(150) | |
| purpose | varchar(20) | lecture / examination / meeting / workshop / conference / event |
| date | date | |
| start_time, end_time | time | |
| attendance | int | |
| equipment_note | varchar(255) | |
| status | varchar(12) | pending / approved / rejected / cancelled / completed |
| approved_by | varchar(150) | |

---

## Approvals

### `approvals_approvalstep`
| Field | Type | Notes |
|---|---|---|
| booking_id | FK → booking | |
| routed_to_department_id | FK → department | the room's owning unit |
| decision | varchar(10) | approved / rejected / returned |
| decided_by_id | FK → user | |
| comment | varchar(255) | |
| decided_at | datetime | |

---

## Usage

### `usage_usagelog`
Historical status changes (concept note 8.4).

| Field | Type | Notes |
|---|---|---|
| room_id | FK → room | |
| status | varchar(20) | the new status |
| changed_by_id | FK → user | |
| note | varchar(200) | |
| timestamp | datetime | |

---

## Notifications

### `notifications_notification`
| Field | Type | Notes |
|---|---|---|
| user_id | FK → user | recipient |
| message | varchar(300) | |
| is_read | bool | |
| created_at | datetime | |

---

## Audit

### `audit_auditlog`
Immutable record of material changes (concept note 7.8).

| Field | Type | Notes |
|---|---|---|
| timestamp | datetime | |
| user_id | FK → user | who made the change |
| action | varchar(80) | e.g. Status change, Booking approved |
| target | varchar(200) | affected room / record |
| previous_value | varchar(200) | |
| new_value | varchar(200) | |
