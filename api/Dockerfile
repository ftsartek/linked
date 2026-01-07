# syntax=docker.io/docker/dockerfile-upstream:1.19.0
FROM debian:trixie-slim

# Set persistent environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    UV_PYTHON_INSTALL_DIR=/opt/uv \
    UV_CACHE_DIR=/var/cache/uv

# Preseed data mount
VOLUME /data/preseed

# Set up working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    supervisor \
    cron \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy application files
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY static/preseed/curated/ ./static/preseed/curated/

# Copy configuration files
COPY supervisord.conf /etc/supervisor/supervisord.conf
COPY entrypoint.sh /entrypoint.sh

# Create virtual environment, sync dependencies, and set up directories
RUN uv sync --frozen && \
    mkdir -p /data/preseed/sde /var/cache/uv && \
    chown -R www-data:www-data /data/preseed /var/cache/uv /opt/uv /app && \
    chmod +x /entrypoint.sh

ENV PATH=/app/.venv/bin:$PATH

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]
