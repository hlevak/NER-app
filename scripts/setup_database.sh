#!/bin/bash
set -e

echo "============================================"
echo " NER-app: Database Setup"
echo "============================================"
echo ""

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$APP_DIR/config/label-studio.env"
SQL_FILE="$APP_DIR/config/postgresql-init.sql"

if [ ! -f "$ENV_FILE" ]; then
    echo "ERROR: Environment file not found: $ENV_FILE"
    exit 1
fi

# Load environment variables
export $(grep -v '^#' "$ENV_FILE" | xargs)

echo "Database configuration:"
echo "  Host: ${POSTGRE_HOST:-localhost}"
echo "  Port: ${POSTGRE_PORT:-5432}"
echo "  Name: ${POSTGRE_NAME:-label_studio}"
echo "  User: ${POSTGRE_USER:-label_studio_user}"
echo ""

# Check if PostgreSQL is running
if ! pg_isready -h "${POSTGRE_HOST:-localhost}" -p "${POSTGRE_PORT:-5432}" > /dev/null 2>&1; then
    echo "ERROR: PostgreSQL is not running on ${POSTGRE_HOST:-localhost}:${POSTGRE_PORT:-5432}"
    echo "Please start PostgreSQL first:"
    echo "  sudo service postgresql start"
    exit 1
fi

echo "PostgreSQL is running ✓"
echo ""

# Ask for postgres password
echo "Enter PostgreSQL superuser (postgres) password:"
read -s POSTGRES_PASSWORD
echo ""

# Create database and user
export PGPASSWORD="$POSTGRES_PASSWORD"

# Check if we can connect as postgres
if ! psql -U postgres -h "${POSTGRE_HOST:-localhost}" -p "${POSTGRE_PORT:-5432}" -c "SELECT 1;" > /dev/null 2>&1; then
    echo "ERROR: Cannot connect as postgres user. Check password and try again."
    exit 1
fi

echo "Creating database and user..."

# Create user
psql -U postgres -h "${POSTGRE_HOST:-localhost}" -p "${POSTGRE_PORT:-5432}" << EOF
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${POSTGRE_USER:-label_studio_user}') THEN
        CREATE ROLE ${POSTGRE_USER:-label_studio_user} WITH LOGIN PASSWORD '${POSTGRE_PASSWORD:-LabelStudio2024!}';
        RAISE NOTICE 'User ${POSTGRE_USER:-label_studio_user} created';
    ELSE
        RAISE NOTICE 'User ${POSTGRE_USER:-label_studio_user} already exists';
    END IF;
END
\$\$;
EOF

# Create database if not exists
psql -U postgres -h "${POSTGRE_HOST:-localhost}" -p "${POSTGRE_PORT:-5432}" -tc "SELECT 1 FROM pg_database WHERE datname = '${POSTGRE_NAME:-label_studio}'" | grep -q 1 || \
    psql -U postgres -h "${POSTGRE_HOST:-localhost}" -p "${POSTGRE_PORT:-5432}" -c "CREATE DATABASE ${POSTGRE_NAME:-label_studio} OWNER ${POSTGRE_USER:-label_studio_user} ENCODING 'UTF8';"

# Grant privileges
psql -U postgres -h "${POSTGRE_HOST:-localhost}" -p "${POSTGRE_PORT:-5432}" -c "GRANT ALL PRIVILEGES ON DATABASE ${POSTGRE_NAME:-label_studio} TO ${POSTGRE_USER:-label_studio_user};"

# Set up schema permissions
psql -U postgres -h "${POSTGRE_HOST:-localhost}" -p "${POSTGRE_PORT:-5432}" -d "${POSTGRE_NAME:-label_studio}" << EOF
GRANT ALL ON SCHEMA public TO ${POSTGRE_USER:-label_studio_user};
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ${POSTGRE_USER:-label_studio_user};
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ${POSTGRE_USER:-label_studio_user};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${POSTGRE_USER:-label_studio_user};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${POSTGRE_USER:-label_studio_user};
EOF

unset PGPASSWORD

echo ""
echo "============================================"
echo " Database setup complete!"
echo ""
echo " Database: ${POSTGRE_NAME:-label_studio}"
echo " User: ${POSTGRE_USER:-label_studio_user}"
echo ""
echo " You can now start Label Studio:"
echo "  ./scripts/start_label_studio.sh"
echo "============================================"
