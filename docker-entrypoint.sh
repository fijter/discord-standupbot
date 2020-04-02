#!/bin/sh
set -e

export PGDATABASE=${DATABASE_NAME}
export PGUSER=${DATABASE_USER}
export PGPASSWORD=${DATABASE_PASSWORD}
export PGHOST=${DATABASE_HOST}
export PGPORT=${DATABASE_PORT}

until psql -l; do
    >&2 echo "Postgres is unavailable - sleeping"
    sleep 1
done

>&2 echo "Postgres is up - continuing"

if [ "x$DJANGO_MANAGEPY_MIGRATE" = 'xon' ]; then
    python manage.py migrate --noinput
fi

exec "$@"
