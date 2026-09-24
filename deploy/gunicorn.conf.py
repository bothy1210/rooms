"""
Gunicorn configuration — UZ Room System.

Referenced by the systemd unit:
    gunicorn --config /opt/roomsys/deploy/gunicorn.conf.py config.wsgi:application

Worker count follows the common (2 x CPU cores) + 1 rule; tune for the server.
"""
import multiprocessing

# Bind to the systemd-managed Unix socket (Nginx proxies to this).
bind = "unix:/run/roomsys.sock"

# Workers
workers = multiprocessing.cpu_count() * 2 + 1
# Threads let each worker keep serving while one request waits on the database
# or builds a PDF export, so many simultaneous users don't queue behind it.
# Each thread holds its own DB connection (CONN_MAX_AGE): keep
# workers x threads under PostgreSQL's max_connections (default 100).
worker_class = "gthread"
threads = 4
timeout = 60
graceful_timeout = 30
keepalive = 5

# Recycle workers periodically to bound memory use.
max_requests = 1000
max_requests_jitter = 100

# Logging (journald captures stdout/stderr via systemd).
accesslog = "-"
errorlog = "-"
loglevel = "info"

proc_name = "roomsys"
