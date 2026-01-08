#!/bin/bash
set -e

LOCKFILE="/var/lib/linked/preseed/collected.lock"

# Run migrations (safe to run each time)
echo "Running database migrations..."
uv run linked migrate

# One-time data collection and preseed
if [ ! -f "$LOCKFILE" ]; then
    echo "Collecting static data..."
    uv run linked collect all

    echo "Preseeding database..."
    uv run linked preseed

    touch "$LOCKFILE"
    echo "Initial setup complete."
else
    echo "Data already collected, skipping..."
fi

if [ ! -f "/etc/linked/crontab" ]; then
    echo "Copying crontab..."
    cp /var/www/.crontab /etc/linked/crontab
fi

if [ ! -f "/etc/linked/supervisord.conf" ]; then
    echo "Copying supervisord.conf..."
    cp /var/www/.supervisord.conf /etc/linked/supervisord.conf
fi

exec "$@"
