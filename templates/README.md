# Templates — UZ Room Inventory & Usage Monitoring System

Server-rendered HTML for the Django project (Bootstrap-style CSS + HTMX + Alpine +
Chart.js). Drop this `templates/` folder into the project root, alongside `apps/`,
`config/` and `static/`. `config/settings/base.py` already points `TEMPLATES['DIRS']`
at this folder.

## Layout
- `base.html` — Omhare-themed shell (crest header, sidebar, messages, drawer target)
- `partials/` — `_sidebar.html`, `_scope_switcher.html`
- `accounts/` — login, profile, user list, forbidden
- `rooms/` — inventory, register, `partials/_room_drawer.html`, forbidden
- `bookings/` — booking form, list, find_venue, calendar, `partials/_availability_result.html`
- `approvals/` — pending queue
- `dashboards/` — dashboard, reports, forbidden
- `notifications/` — list
- `audit/` — trail
- `usage/` — history
- `reports/` — `utilisation_pdf.html` (rendered to PDF by WeasyPrint)

## Requires
The static assets in `static/` (omhare.css, app.css, htmx.min.js, alpine.min.js,
chart.min.js, app.js, uz-crest.png) and the `ui_extras` template tags in
`apps/core/templatetags/`. Both ship with the main project zip.

All 24 templates were verified to render (HTTP 200) via the Django test client.
