FROM debian:trixie-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    npm \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy package files first for better caching
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy source files
COPY src/ ./src/
COPY static/ ./static/
COPY svelte.config.js vite.config.ts tsconfig.json ./

# Build production bundle
RUN npm run build

# Copy supervisor configuration
COPY supervisord.conf /etc/supervisor/supervisord.conf

# Set ownership of app directory
RUN chown -R www-data:www-data /app

EXPOSE 3000

CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
