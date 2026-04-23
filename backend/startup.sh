#!/usr/bin/env bash
set -euo pipefail

# App Service runs this on container start.
# $PORT is provided by the platform.

# The appsvc/python image ships without MSSQL drivers, so install once per
# container instance before alembic tries to open an Azure SQL connection.
if ! odbcinst -q -d -n "ODBC Driver 18 for SQL Server" >/dev/null 2>&1; then
  echo "Installing msodbcsql18..."
  export DEBIAN_FRONTEND=noninteractive
  curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
    | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg
  echo "deb [signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
    > /etc/apt/sources.list.d/mssql-release.list
  apt-get update -y
  ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 unixodbc
  apt-get clean
  rm -rf /var/lib/apt/lists/*
fi

python -m alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
