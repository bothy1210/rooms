# Centralised Room Inventory & Usage Monitoring System
## System Architecture & File Structure

**University of Zimbabwe · Part of the Omhare University Information System family**

Stack: **Django 5 · PostgreSQL 16 · Bootstrap 5 + HTMX + Alpine.js · Gunicorn + Nginx + systemd on Ubuntu (no Docker)**

---

## 1. Technology Stack & Rationale

| Layer | Choice | Why |
|---|---|---|
| Operating system | Ubuntu Server 24.04 LTS | University standard, long support, no Docker needed |
| Language / framework | Python 3.12 + **Django 5.x** | Auth, ORM, migrations, admin, permissions and forms are built in — most of this system's needs (RBAC, workflow, audit) come "for free" |
| Data access | Django ORM + **psycopg 3** | Native PostgreSQL driver, no ORM lock-in for raw reports |
| Database | **PostgreSQL 16** (native install) | Recommended in the concept note; reliable, open-source, strong for structured institutional records |
| Templating / UI | Django Templates + **Bootstrap 5** | Matches the Omhare UIS look; maintainable by staff with minimal training |
| Interactivity | **HTMX** + **Alpine.js** | Live filtering, drawers, conflict checks and scope switching *without* a separate React build pipeline — keeps deployment simple |
| Charts | **Chart.js** | Reproduces the utilisation donut and building bars |
| PDF reports | **WeasyPrint** | HTML-to-PDF, reuses existing templates |
| Excel reports | **openpyxl** | Native `.xlsx` export for planning meetings |
| Auth | Django auth + custom `User` (R-number) | Optionally federates to Omhare via LDAP/SSO |
| Web server | **Gunicorn** (WSGI) behind **Nginx** | Battle-tested, systemd-managed, no containers |
| Scheduled jobs | **cron** + Django management commands | Booking reminders, pending-approval nudges, annual room census |
| Async email (optional) | Celery + Redis | Only if high email volume; otherwise SMTP synchronously |

> **Alternative considered:** Django REST Framework + a React SPA. Rejected as the primary path because it adds a Node build pipeline and a second deployment artifact — extra operational load for a university team running without Docker. The service layer below is API-ready, so a React or mobile client can be added later against the same backend.

---

## 2. Architectural Layers

The system is a layered monolith. Business rules (conflict detection, scoping, workflow routing) live in a **service layer**, never in templates — so they can be reused by web views, scheduled jobs, and any future API.

```
┌─────────────────────────────────────────────────────────────┐
│  PRESENTATION                                                │
│  Django templates · Bootstrap 5 · HTMX · Alpine.js · Chart.js│
│  (Omhare-themed base layout, crest + navy/orange header)     │
└───────────────┬─────────────────────────────────────────────┘
                │ HTTP (HTMX partials / full pages)
┌───────────────▼─────────────────────────────────────────────┐
│  APPLICATION      Views · Forms · URL routing · Mixins       │
│  (thin — delegates to services; enforces auth & scope)       │
└───────────────┬─────────────────────────────────────────────┘
                │ function calls
┌───────────────▼─────────────────────────────────────────────┐
│  DOMAIN / SERVICE LAYER                                      │
│  services.py  → write operations & business rules            │
│  selectors.py → scoped read queries                          │
│  • BookingService.check_conflicts() / suggest_alternatives() │
│  • RoomRegistrationService (Draft → Verified → code)         │
│  • ApprovalService.route() / decide()                        │
│  • ScopeService (My Dept / My Faculty / University-wide)     │
└───────────────┬─────────────────────────────────────────────┘
                │ Django ORM (psycopg 3)
┌───────────────▼─────────────────────────────────────────────┐
│  DATA          PostgreSQL 16  (rooms, bookings, users, logs) │
└─────────────────────────────────────────────────────────────┘

Cross-cutting: Authentication & RBAC · Scope enforcement ·
Audit logging (signals/middleware) · Notifications
```

**Two hierarchies, modelled explicitly** (the core design decision from our discussion):
- **Physical:** Campus → Building → Floor → Room  → drives room codes & location search
- **Organisational:** University → Faculty → Department → Room  → drives permissions, scoped dashboards & approval routing

---

## 3. Deployment Topology (single server, no Docker)

Everything runs as native services on one Ubuntu host. Nginx terminates TLS and serves static files; Gunicorn runs Django behind a Unix socket; PostgreSQL listens on localhost only.

```
                          Internet / UZ network
                                   │  HTTPS 443
                          ┌────────▼─────────┐
                          │      Nginx       │  TLS, static/media, reverse proxy
                          │  (systemd unit)  │
                          └────────┬─────────┘
                                   │ unix socket  /run/roomsys.sock
                          ┌────────▼─────────┐
                          │     Gunicorn     │  3–4 workers, WSGI
                          │  (systemd unit)  │
                          └────────┬─────────┘
                                   │ Django app (venv)
                 ┌─────────────────┼──────────────────┐
                 │                 │                  │
        ┌────────▼──────┐  ┌───────▼───────┐  ┌───────▼────────┐
        │  PostgreSQL   │  │  cron jobs    │  │ Redis (opt.)   │
        │  127.0.0.1    │  │ reminders /   │  │ Celery broker  │
        │  :5432        │  │ census        │  │ if async email │
        └───────────────┘  └───────────────┘  └────────────────┘

Filesystem:
  /opt/roomsys/            → application code (git checkout)
  /opt/roomsys/venv/       → Python virtual environment
  /var/roomsys/media/      → uploaded room photos
  /var/roomsys/static/     → collected static files (served by Nginx)
  /etc/roomsys/.env        → secrets (DB password, SECRET_KEY, SMTP)
```

---

## 4. Request Lifecycle (example: submitting a booking)

1. Browser posts the booking form (or an HTMX partial for the live availability check).
2. **Nginx** forwards to **Gunicorn** → Django URL router → `bookings.views.booking_create`.
3. The view checks the user is authenticated and **in-scope**, then calls `BookingService.check_conflicts(room, date, start, end, purpose, attendance)`.
4. The service runs the rules: time-overlap conflict, capacity check, **suitability-tag** check; if it fails it calls `suggest_alternatives()` (university-wide, capacity-ranked).
5. On success it creates the `Booking` (status *Pending*), and `ApprovalService.route()` sends it to the **owning** department/faculty office (cross-unit requests route to the owner, not the requester's unit).
6. A `post_save` **signal** writes an `AuditLog` row and queues a `Notification`.
7. The view returns an HTMX partial that updates the page without a full reload.

---

## 5. Django Apps → Concept-Note Modules

Each of the eight modules maps to a focused Django app under `apps/`:

| Django app | Concept-note module(s) | Key responsibilities |
|---|---|---|
| `core` | Shared foundation | Base templates, org/physical hierarchy models (Campus, Building, Faculty, Department), mixins, scope service |
| `accounts` | 7.6 User Management | Custom `User` (R-number), roles, department/faculty scoping, RBAC, login/SSO |
| `rooms` | 7.1 Room Inventory | Rooms, room types, **suitability tags**, equipment, **Draft→Verified registration workflow**, room codes |
| `usage` | 7.2 Room Usage Status | Live status, usage log table |
| `bookings` | 7.3 Booking & Scheduling | Requests, **conflict detection**, **Find-a-Venue** capacity search, calendar |
| `approvals` | 7.4 Approval Workflow | Routing to responsible office, approve/reject/return |
| `dashboards` | 7.5 Dashboard & Reporting | **Scoped** dashboards, utilisation stats, PDF/Excel export |
| `notifications` | 7.7 Notifications | Email + in-app notifications, reminders |
| `audit` | 7.8 Audit Trail | Signal-based change logging (user, time, old → new) |

---

## 6. Complete File & Folder Structure

```
roomsys/                                  # ── project root (git repo) ──
│
├── manage.py                             # Django CLI entry point
├── requirements.txt                      # pinned Python dependencies
├── requirements-dev.txt                  # test/lint tools
├── .env.example                          # template for /etc/roomsys/.env
├── .gitignore
├── README.md
├── ARCHITECTURE.md                       # this document
├── pytest.ini                            # test config
│
├── config/                               # ── project configuration ──
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py                       # shared settings (apps, middleware, templates)
│   │   ├── development.py                # DEBUG=True, local DB
│   │   ├── production.py                 # DEBUG=False, security headers, prod DB
│   │   └── test.py                       # fast test settings
│   ├── urls.py                           # root URL router (includes each app)
│   ├── wsgi.py                           # Gunicorn entry point
│   └── asgi.py                           # (future websockets / async)
│
├── apps/                                 # ── all business modules ──
│   │
│   ├── core/                             # shared foundation + hierarchy
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py                     # Campus, Building, Floor, Faculty, Department
│   │   ├── mixins.py                     # LoginRequired, ScopeRequired, AdminScopedMixin
│   │   ├── services.py                   # ScopeService (My Dept / Faculty / University)
│   │   ├── selectors.py                  # reusable scoped querysets
│   │   ├── context_processors.py         # inject org tree + current scope into templates
│   │   ├── templatetags/
│   │   │   ├── __init__.py
│   │   │   └── ui_extras.py              # status pills, capacity tags, badges
│   │   ├── migrations/
│   │   └── tests/
│   │       ├── test_models.py
│   │       └── test_scope.py
│   │
│   ├── accounts/                         # users, roles, permissions
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py                     # User (R-number), Role, UserScope
│   │   ├── managers.py                   # custom UserManager
│   │   ├── backends.py                   # optional LDAP/Omhare SSO backend
│   │   ├── permissions.py                # role → capability matrix
│   │   ├── forms.py                      # login, user create/edit
│   │   ├── views.py                      # login, logout, profile, user admin
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── migrations/
│   │   └── tests/
│   │       └── test_permissions.py
│   │
│   ├── rooms/                            # inventory + registration workflow
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py                     # Room, RoomType, SuitabilityTag, Equipment,
│   │   │                                 #   RoomStatus (enum), RoomDraft
│   │   ├── services.py                   # RoomRegistrationService:
│   │   │                                 #   submit_draft() → verify() → issue_code()
│   │   ├── selectors.py                  # search/filter, scoped room lists
│   │   ├── forms.py                      # room register / edit forms
│   │   ├── views.py                      # inventory list, detail drawer, register, verify
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── signals.py                    # status-change → audit
│   │   ├── migrations/
│   │   └── tests/
│   │       ├── test_registration.py      # Draft → Verified → code
│   │       └── test_search.py
│   │
│   ├── usage/                            # live status + usage log
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py                     # UsageLog
│   │   ├── services.py                   # update_status()
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── migrations/
│   │   └── tests/
│   │
│   ├── bookings/                         # requests, conflict detection, find-a-venue
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py                     # Booking, BookingStatus (enum)
│   │   ├── services.py                   # BookingService.check_conflicts(),
│   │   │                                 #   suggest_alternatives(), create_request()
│   │   ├── selectors.py                  # find_venues_by_capacity() (university-wide)
│   │   ├── forms.py                      # booking request, venue search
│   │   ├── views.py                      # booking form, live check (HTMX), calendar,
│   │   │                                 #   find-a-venue results
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── signals.py
│   │   ├── migrations/
│   │   └── tests/
│   │       ├── test_conflicts.py         # double-booking prevention
│   │       ├── test_suitability.py       # purpose → tag matching
│   │       └── test_find_venue.py        # cross-faculty capacity search
│   │
│   ├── approvals/                        # workflow routing
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py                     # ApprovalStep, ApprovalRoute
│   │   ├── services.py                   # ApprovalService.route() / decide()
│   │   ├── views.py                      # pending queue, approve/reject
│   │   ├── urls.py
│   │   ├── migrations/
│   │   └── tests/
│   │       └── test_routing.py           # cross-unit → owning office
│   │
│   ├── dashboards/                       # scoped dashboards + reports
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── services.py                   # aggregate stats within a scope
│   │   ├── selectors.py                  # utilisation by dept / building / type
│   │   ├── views.py                      # dashboard, report pages
│   │   ├── urls.py
│   │   ├── exports/
│   │   │   ├── pdf.py                    # WeasyPrint report builder
│   │   │   └── excel.py                  # openpyxl workbook builder
│   │   ├── migrations/
│   │   └── tests/
│   │
│   ├── notifications/                    # email + in-app
│   │   ├── __init__.py
│   │   ├── apps.py
│   │   ├── models.py                     # Notification
│   │   ├── services.py                   # notify(), send_email()
│   │   ├── views.py                      # notification list / mark read
│   │   ├── urls.py
│   │   ├── migrations/
│   │   └── tests/
│   │
│   └── audit/                            # audit trail
│       ├── __init__.py
│       ├── apps.py
│       ├── models.py                     # AuditLog (user, action, target, old, new, ts)
│       ├── middleware.py                 # captures current user for signals
│       ├── services.py                   # log_change()
│       ├── views.py                      # audit trail table (filterable)
│       ├── urls.py
│       ├── migrations/
│       └── tests/
│
├── templates/                            # ── server-rendered HTML ──
│   ├── base.html                         # Omhare-themed shell: crest, navy/orange header,
│   │                                     #   sidebar, "Welcome R2289…", Logout
│   ├── partials/
│   │   ├── _sidebar.html
│   │   ├── _topbar.html
│   │   ├── _scope_switcher.html          # My Dept / My Faculty / University-wide
│   │   ├── _notifications.html
│   │   ├── _room_drawer.html             # HTMX-loaded room detail
│   │   └── _pagination.html
│   ├── accounts/         (login.html, profile.html, user_list.html …)
│   ├── rooms/            (inventory.html, register.html, verify_queue.html …)
│   ├── bookings/         (booking_form.html, calendar.html, find_venue.html,
│   │                      _availability_result.html …)
│   ├── approvals/        (pending.html)
│   ├── dashboards/       (dashboard.html, report_building.html …)
│   ├── notifications/    (list.html)
│   ├── audit/            (trail.html)
│   └── reports/          (pdf_base.html — print stylesheet for WeasyPrint)
│
├── static/                               # ── source static assets ──
│   ├── css/
│   │   ├── omhare.css                    # UZ palette (navy #0E1B3D, orange), header styling
│   │   └── app.css
│   ├── js/
│   │   ├── htmx.min.js
│   │   ├── alpine.min.js
│   │   ├── chart.min.js
│   │   └── app.js                        # small helpers (calendar, drawers)
│   └── img/
│       ├── uz-crest.png
│       └── omhare-logo.png
│
├── deploy/                               # ── no-Docker deployment ──
│   ├── nginx/
│   │   └── roomsys.conf                  # server block, static/media, proxy to socket
│   ├── systemd/
│   │   ├── roomsys.service               # Gunicorn service unit
│   │   └── roomsys.socket                # (optional socket activation)
│   ├── gunicorn.conf.py                  # workers, bind, timeouts
│   ├── cron/
│   │   └── roomsys.cron                  # reminders, census schedule
│   └── DEPLOY.md                         # step-by-step server setup runbook
│
├── scripts/
│   ├── backup_db.sh                      # pg_dump nightly backup
│   └── restore_db.sh
│
└── docs/
    ├── CONCEPT_NOTE.pdf
    ├── data-dictionary.md                # tables & fields (concept note §8)
    └── user-guide.md
```

---

## 7. Key Files Explained

**`config/settings/` (split settings).** `base.py` holds everything common; `development.py` and `production.py` import from it and override `DEBUG`, `ALLOWED_HOSTS`, database host, and security headers. Secrets are never in code — they are read from `/etc/roomsys/.env` via `django-environ`.

**Service layer (`services.py` / `selectors.py`).** Views stay thin. All write-side business rules live in `services.py` (e.g. `BookingService.check_conflicts`), and all scoped reads live in `selectors.py` (e.g. `find_venues_by_capacity`). This keeps the rules testable in isolation and reusable by cron jobs and any future API.

**Scope enforcement (`core/mixins.py` + `core/services.py`).** `ScopeService` resolves the three dashboard scopes and every list view mixes in `AdminScopedMixin`, which filters querysets to the user's department/faculty unless they are central admin. This is what makes the dashboard relevant per-user instead of showing all 254 rooms to everyone.

**Audit via signals (`audit/`).** A lightweight middleware stashes the current user; `post_save`/`pre_save` signals on `Room`, `Booking`, etc. write an `AuditLog` row with the previous and new values — satisfying §7.8 without cluttering the views.

---

## 8. PostgreSQL Setup — Native, No Docker

Install and create the database and a dedicated least-privilege role directly on the server:

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib

# create role and database
sudo -u postgres psql <<'SQL'
CREATE ROLE roomsys WITH LOGIN PASSWORD 'change-me-strong';
CREATE DATABASE roomsys_db OWNER roomsys;
GRANT ALL PRIVILEGES ON DATABASE roomsys_db TO roomsys;
ALTER ROLE roomsys SET client_encoding TO 'utf8';
ALTER ROLE roomsys SET timezone TO 'Africa/Harare';
SQL
```

Django reads these from `.env`:

```ini
# /etc/roomsys/.env
DATABASE_URL=postgres://roomsys:change-me-strong@127.0.0.1:5432/roomsys_db
SECRET_KEY=...
DEBUG=False
ALLOWED_HOSTS=rooms.uz.ac.zw
EMAIL_HOST=smtp.uz.ac.zw
```

```python
# config/settings/base.py  (excerpt)
import environ
env = environ.Env()
DATABASES = {"default": env.db("DATABASE_URL")}
```

Then run migrations and create the first admin:

```bash
source /opt/roomsys/venv/bin/activate
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

Nightly backups via `scripts/backup_db.sh` (`pg_dump roomsys_db | gzip > …`) scheduled in cron. PostgreSQL binds to `127.0.0.1` only, so it is never exposed to the network.

---

## 9. Deployment Without Docker

**Gunicorn** runs Django and is supervised by **systemd**:

```ini
# deploy/systemd/roomsys.service
[Unit]
Description=Room System (Gunicorn)
After=network.target postgresql.service

[Service]
User=roomsys
Group=www-data
WorkingDirectory=/opt/roomsys
EnvironmentFile=/etc/roomsys/.env
ExecStart=/opt/roomsys/venv/bin/gunicorn \
    --config /opt/roomsys/deploy/gunicorn.conf.py \
    config.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

**Nginx** terminates TLS, serves static/media, and proxies everything else to Gunicorn over a Unix socket. **cron** runs the scheduled Django commands:

```cron
# deploy/cron/roomsys.cron
*/15 * * * *  roomsys  /opt/roomsys/venv/bin/python /opt/roomsys/manage.py send_reminders
0 7 * * *     roomsys  /opt/roomsys/venv/bin/python /opt/roomsys/manage.py nudge_pending_approvals
0 2 1 8 *     roomsys  /opt/roomsys/venv/bin/python /opt/roomsys/manage.py open_room_census
```

Bring-up sequence: `sudo systemctl enable --now postgresql roomsys nginx`. The full runbook lives in `deploy/DEPLOY.md`.

---

## 10. Security & Access Control

- **Role-based access** (concept §9.14): three top-level roles — Central Administrator, Admin (scoped), Read-Only Viewer — mapped to a capability matrix in `accounts/permissions.py`.
- **Scoped admin** (concept §6, §11): an admin's writes are constrained to their own department/faculty at the queryset level, so a Geoinformatics secretary can never edit another unit's rooms even by tampering with URLs.
- **CSRF, session security, HTTPS-only cookies, HSTS** enabled in `production.py`.
- **Audit trail** on every material change for accountability.
- PostgreSQL reachable only from localhost; secrets only in `/etc/roomsys/.env` (mode `600`).

---

## 11. Integration with Omhare UIS (optional but recommended)

Because this system belongs to the same UZ information-system family, users ideally sign in with the **same R-number** they use for Omhare. Two options, both supported by the `accounts/backends.py` hook:

1. **LDAP / Active Directory** — authenticate against the central directory; map directory groups to system roles.
2. **SSO (SAML/OAuth2)** — redirect to the university identity provider; the room system only stores role and scope, not passwords.

Until that integration is in place, Django's built-in auth is used as a self-contained fallback, so the system can go live independently and federate later without schema changes.

---

## 12. Data Model Summary

Core tables (expanding the concept note §8 with the two-hierarchy and suitability design):

- **Org / physical:** `campus`, `building`, `floor`, `faculty`, `department`
- **Rooms:** `room`, `room_type`, `suitability_tag`, `room_suitability` (M2M), `equipment`, `room_equipment` (M2M), `room_draft`
- **Usage:** `usage_log`
- **Bookings:** `booking`, `approval_step`
- **People:** `user`, `role`, `user_scope`
- **System:** `notification`, `audit_log`

Every `room` carries **both** a `building`/`floor` (physical) and a `department`/`faculty` (organisational) foreign key, plus a many-to-many `suitability_tag` set — the three relationships that power location search, scoped dashboards, and purpose-aware booking respectively.
