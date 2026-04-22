#!/usr/bin/env bash
set -euo pipefail

# App Service runs this on container start.
# $PORT is provided by the platform.
python -m alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
