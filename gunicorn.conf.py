# Gunicorn configuration for Railway deployment
import os

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
backlog = 2048

# Worker processes
workers = 2
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 2
max_requests = 1000
max_requests_jitter = 100

# Restart workers after this many requests, with up to this much jitter added
preload_app = True
worker_tmp_dir = "/dev/shm"  # Use memory for worker temporary files

# Logging
loglevel = "info"
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr

# Process naming
proc_name = "dulceria_pos"

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Performance
worker_rlimit_nofile = 1024