# Base image for always-running services
FROM python:3.10-slim

ENV DEBIAN_FRONTEND=noninteractive

# Service-specific system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    && rm -rf /var/lib/apt/lists/*

# Service-focused Python dependencies
RUN pip install --no-cache-dir \
    kubernetes \
    paho-mqtt \
    flask \
    flask-cors \
    requests \
    pyyaml \
    python-dateutil \
    "braingeneers[iot]" \
    numpy \
    pandas

# Install shared utilities
COPY shared/ /usr/local/lib/python3.10/site-packages/maxwell_shared/
ENV PYTHONPATH="/usr/local/lib/python3.10/site-packages:$PYTHONPATH"

# Service configuration
ENV SERVICE_TYPE="service"
WORKDIR /app

# Health check for services
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1
