#!/bin/sh
set -eu

# Both the API and bot must see the migrated schema before they start.
# Settings validation fails here too, before any HTTP port is opened.
echo "Applying database migrations..."
alembic upgrade head

exec /usr/bin/supervisord -c /etc/supervisor/arena.conf
