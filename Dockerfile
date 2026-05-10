# ─────────────────────────────────────────────────────────────────────────────
#  Blacklist Microservice — Dockerfile
#  Universidad de los Andes — DevOps Entrega 3
#  Edwin Alexander Cifuentes Bastidas
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.11-slim

# Variables de entorno para Python
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencias del sistema necesarias para psycopg (PostgreSQL)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Instalación de dependencias Python (capa cacheable)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install gunicorn

# Código de la aplicación
COPY application.py .
COPY app/ ./app/

# Puerto donde escucha gunicorn
EXPOSE 5000

# Health check del contenedor (Fargate también lo usa para marcar UNHEALTHY)
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Servidor WSGI de producción
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "2", \
     "--threads", "2", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "application:application"]
