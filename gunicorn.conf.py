# Configuración optimizada de Gunicorn para Render.com
# Este archivo configura Gunicorn para usar menos memoria y evitar timeouts

import multiprocessing
import os

# Número de workers (procesos)
# Render free tier tiene 512MB RAM, usamos 1 worker para no exceder memoria
workers = 1

# Número de threads por worker
# Aumentamos threads en lugar de workers para mejor performance con menos memoria
threads = 2

# Timeout en segundos (default es 30, lo aumentamos por las importaciones pesadas)
timeout = 120

# Bind (puerto y host)
bind = f"0.0.0.0:{os.environ.get('PORT', '10000')}"

# Worker class
# sync es más estable y usa menos memoria que gevent/eventlet
worker_class = "sync"

# Maximum requests per worker (restart workers periódicamente para liberar memoria)
max_requests = 1000
max_requests_jitter = 50

# Preload application (carga la app antes de fork, ahorra memoria)
preload_app = True

# Timeout para graceful shutdown
graceful_timeout = 30

# Keep alive
keepalive = 2

# Logging
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = "info"

# Worker tmp directory (use /dev/shm for better performance)
worker_tmp_dir = "/dev/shm"

# Limit request line size
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190
