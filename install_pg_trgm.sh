#!/bin/bash
set -e

echo "Installing postgresql-contrib-17 for pg_trgm extension..."

# Update package lists
apt-get update

# Install postgresql-contrib for pg_trgm
apt-get install -y postgresql-contrib-17

# Clean up to reduce image size
apt-get clean && rm -rf /var/lib/apt/lists/*

# Ensure the extension is installed in the default database
echo "Creating pg_trgm extension in the database..."
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"