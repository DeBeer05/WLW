# Installation Guide for Other Machines

## Database Requirement

**This project uses PostgreSQL** (no SQLite3 needed).

## Quick Start (Linux - pip only)

**If you only have pip access (no sudo):**

```bash
# Navigate to project
cd back-end/Wirelesworks

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (includes PostgreSQL client)
pip install -r requirements.txt

# Configure database (see Database Setup section below)
# Edit settings.py or use environment variables

# Setup database
python manage.py makemigrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Start server
python manage.py runserver 0.0.0.0:8000
```

**Note:** You need PostgreSQL server access. Contact your system admin for database credentials.

---

## Database Setup

### Option 1: Using Environment Variables (Recommended)

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` with your database credentials:
```bash
DB_NAME=wirelesworks_db
DB_USER=your_username
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

Load environment variables before running Django:
```bash
export $(cat .env | xargs)
python manage.py runserver
```

### Option 2: Edit settings.py directly

Edit `Wirelesworks/settings.py` and update the DATABASES section with your credentials.

### PostgreSQL Server Setup (if you have access)

**Quick Setup Script:**
```bash
# Make script executable
chmod +x setup_db.sh

# Run setup script (creates database and user)
./setup_db.sh
```

**Manual Setup - Ubuntu/Debian:**
```bash
sudo apt-get install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
CREATE DATABASE wirelesworks_db;
CREATE USER wirelesworks_user WITH PASSWORD 'wirelesworks_pass';
GRANT ALL PRIVILEGES ON DATABASE wirelesworks_db TO wirelesworks_user;
\q
```

**Fedora/RHEL:**
```bash
sudo dnf install postgresql postgresql-server
sudo postgresql-setup --initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

---

## Quick Start (Linux - with sudo)

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install python3 python3-pip python3-venv libsqlite3-dev

# Navigate to project
cd back-end/Wirelesworks

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Setup database
python manage.py makemigrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Add serial port permissions
sudo usermod -a -G dialout $USER
# Then logout and login

# Start server
python manage.py runserver
```

---

## Prerequisites

### Python Installation
This project requires Python 3.8+ and PostgreSQL database access.

### Required Software
- Python 3.8 or higher
- PostgreSQL server (local or remote)
- pip (Python package manager)

## Installation Steps

1. **Install Python 3.8+**

2. **Install system dependencies (Linux with sudo)**
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install python3 python3-pip python3-venv
   
   # Install PostgreSQL (optional, if running database locally)
   sudo apt-get install postgresql postgresql-contrib
   
   # For serial port access
   sudo apt-get install python3-serial
   ```

3. **Clone/Copy the project**
   ```bash
   cd back-end/Wirelesworks
   ```

4. **Create virtual environment** (recommended)
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

5. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

6. **Configure database**
   ```bash
   # Copy environment file
   cp .env.example .env
   
   # Edit with your database credentials
   nano .env  # or use any text editor
   
   # Load environment variables
   export $(cat .env | xargs)
   ```

7. **Run migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

8. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

9. **Start server**
   ```bash
   python manage.py runserver
   ```

## Troubleshooting

### Database Connection Errors

**"could not connect to server"**
- Check if PostgreSQL server is running
- Verify database credentials in `.env` or `settings.py`
- Check if database exists: `psql -U postgres -l`

**"FATAL: database does not exist"**
```bash
# Create the database
sudo -u postgres psql
CREATE DATABASE wirelesworks_db;
\q
```

**"FATAL: role does not exist"**
```bash
# Create the user
sudo -u postgres psql
CREATE USER wirelesworks_user WITH PASSWORD 'wirelesworks_pass';
GRANT ALL PRIVILEGES ON DATABASE wirelesworks_db TO wirelesworks_user;
\q
```

### Serial Port Issues (Linux)
**Permission denied error:**
```bash
# Add your user to the dialout group
sudo usermod -a -G dialout $USER

# Logout and login again, or use:
newgrp dialout

# Verify permissions
ls -l /dev/ttyS* /dev/ttyUSB*
```

**Find your serial port:**
```bash
# List all serial ports
ls /dev/tty*

# Common ports:
# - /dev/ttyS0, /dev/ttyS1, /dev/ttyS2 (built-in serial)
# - /dev/ttyUSB0, /dev/ttyUSB1 (USB to serial adapters)
# - /dev/ttyACM0 (Arduino, some USB devices)
```

### Port Already in Use
If port 8000 is already in use:
```bash
python manage.py runserver 8080
```

Or find and kill the process:
```bash
# Find process using port 8000
sudo lsof -i :8000

# Kill it
sudo kill -9 <PID>
```

### WebSocket Port Conflict
If port 8765 is in use, edit `Scan/utils/websocket_server.py` and change the port number.

### Permission Errors on Linux
```bash
sudo usermod -a -G dialout $USER
# Logout and login again
```
