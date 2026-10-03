#!/bin/bash
set -e

service postgresql start

# Set password for postgres user
su - postgres -c "psql -c \"ALTER USER postgres WITH PASSWORD 'postgres';\""

# Allow all connections
CONF_DIR=$(ls -d /etc/postgresql/*/main | head -n 1)
sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/g" "$CONF_DIR/postgresql.conf" || true
echo "host all all 0.0.0.0/0 md5" >> "$CONF_DIR/pg_hba.conf"
echo "host all all ::0/0 md5" >> "$CONF_DIR/pg_hba.conf"

service postgresql restart
echo "PostgreSQL started and configured successfully!"
