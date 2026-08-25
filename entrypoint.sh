#!/bin/bash
set -e

echo "Running database migrations..."
flask db upgrade

echo "Starting gunicorn..."
exec gunicorn --bind "0.0.0.0:${PORT:-8080}" --workers 2 --timeout 120 "app:create_app()"
