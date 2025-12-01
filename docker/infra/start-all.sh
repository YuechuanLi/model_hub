#!/bin/sh
set -e

# Start Redis in background
echo "Starting Redis..."
redis-server --daemonize yes --bind 0.0.0.0

# Hand over to the original Postgres entrypoint
echo "Starting Postgres..."
exec docker-entrypoint.sh "$@"
