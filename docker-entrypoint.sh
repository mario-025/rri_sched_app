#!/bin/bash
# Database initialization script untuk Docker
# Ini akan berjalan setiap kali container MySQL di-start

set -e

echo "================================"
echo "Database Initialization Script"
echo "================================"

# Wait for MySQL to be ready
echo "Waiting for MySQL to be ready..."
until mysql -h localhost -u root -p"${MYSQL_ROOT_PASSWORD}" -e "SELECT 1" > /dev/null 2>&1; do
  printf '.'
  sleep 1
done
echo "✓ MySQL is ready!"

# Create database if not exists
echo "Creating database: ${MYSQL_DATABASE}..."
mysql -h localhost -u root -p"${MYSQL_ROOT_PASSWORD}" <<-EOSQL
    CREATE DATABASE IF NOT EXISTS \`${MYSQL_DATABASE}\`;
    GRANT ALL PRIVILEGES ON \`${MYSQL_DATABASE}\`.* TO '${MYSQL_USER}'@'%';
    FLUSH PRIVILEGES;
    SELECT CONCAT('✓ User ', '${MYSQL_USER}', ' created successfully') AS result;
EOSQL

echo "✓ Database initialization completed!"
