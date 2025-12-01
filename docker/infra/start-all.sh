#!/bin/sh
set -e

# Start Redis in background
echo "Starting Redis..."
redis-server --daemonize yes

# Hand over to the original Postgres entrypoint
echo "Starting Postgres..."
exec docker-entrypoint.sh "$@"
