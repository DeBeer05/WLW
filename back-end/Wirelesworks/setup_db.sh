#!/bin/bash
# Quick setup script for PostgreSQL database

echo "=== WirelesWorks PostgreSQL Setup ==="
echo ""

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL is not installed"
    echo "Install it with: sudo apt-get install postgresql postgresql-contrib"
    exit 1
fi

echo "✓ PostgreSQL is installed"
echo ""

# Database configuration
DB_NAME="wirelesworks_db"
DB_USER="wirelesworks_user"
DB_PASSWORD="wirelesworks_pass"

echo "Creating database and user..."
echo ""

# Create database and user
sudo -u postgres psql << EOF
-- Drop existing database and user if they exist
DROP DATABASE IF EXISTS $DB_NAME;
DROP USER IF EXISTS $DB_USER;

-- Create new database and user
CREATE DATABASE $DB_NAME;
CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;

-- Display result
\l $DB_NAME
\du $DB_USER
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Database setup complete!"
    echo ""
    echo "Database details:"
    echo "  Name: $DB_NAME"
    echo "  User: $DB_USER"
    echo "  Password: $DB_PASSWORD"
    echo "  Host: localhost"
    echo "  Port: 5432"
    echo ""
    echo "Next steps:"
    echo "  1. Copy .env.example to .env"
    echo "  2. Run: python manage.py migrate"
    echo "  3. Run: python manage.py createsuperuser"
    echo "  4. Run: python manage.py runserver"
else
    echo ""
    echo "❌ Database setup failed"
    echo "Make sure PostgreSQL is running and you have sudo access"
    exit 1
fi
