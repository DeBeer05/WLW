# WirelesWorks Backend

Django-based backend for Bluetooth Low Energy (BLE) device scanning and management.

⚠️ **Database is disabled** - All database functionality is turned off. Scan data is not persisted.

## Quick Start

```bash
# 1. Install dependencies (no database packages needed)
pip install -r requirements.txt

# 2. Create virtual environment (optional)
python3 -m venv venv
source venv/bin/activate

# 3. Start server
python manage.py runserver
```

## Project Structure

```
Wirelesworks/
├── manage.py              # Django management script
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── Wirelesworks/         # Main Django project
│   ├── settings.py       # Django settings (DB disabled)
│   ├── urls.py          # URL routing (admin removed)
│   └── wsgi.py          # WSGI config
└── Scan/                # BLE scanning app
    ├── models.py        # Models (commented out, DB disabled)
    ├── views.py         # API endpoints (no DB calls)
    ├── urls.py          # App URL routing
    ├── admin.py         # Disabled
    ├── apps.py          # App config (WebSocket auto-start)
    ├── utils/           # Utility modules
    │   ├── websocket_server.py
    │   └── loading.py
    └── yaml_files/      # Configuration files
        ├── company_identifiers.yaml
        └── ad_types.yaml
```

## API Endpoints

- `POST /scan/api/start/` - Start a BLE scan (data not saved)
- `GET /scan/api/history/` - Returns empty (database disabled)
- `GET /scan/api/details/<id>/` - Returns empty (database disabled)
- `GET /scan/` - Info message

## Features

- ✅ BLE device scanning with serial communication
- ✅ Company identifier decoding
- ✅ Device name extraction
- ✅ Real-time WebSocket updates
- ✅ REST API endpoints
- ✅ Automatic WebSocket server startup
- ❌ **Database persistence disabled**
- ❌ **Django admin panel disabled**

## Current Configuration

**Database:** Disabled (`DATABASES = {}`)

**Installed Apps:**
- `django.contrib.staticfiles`
- `Scan`

**Middleware:** Only security and static file middleware

## Enabling Database

To re-enable PostgreSQL database functionality:

1. Edit `Wirelesworks/settings.py`:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': os.environ.get('DB_NAME', 'wirelesworks_db'),
           'USER': os.environ.get('DB_USER', 'wirelesworks_user'),
           'PASSWORD': os.environ.get('DB_PASSWORD', 'wirelesworks_pass'),
           'HOST': os.environ.get('DB_HOST', 'localhost'),
           'PORT': os.environ.get('DB_PORT', '5432'),
       }
   }
   ```

2. Add database apps back to `INSTALLED_APPS`:
   ```python
   'django.contrib.admin',
   'django.contrib.auth',
   'django.contrib.contenttypes',
   'django.contrib.sessions',
   'django.contrib.messages',
   ```

3. Update `requirements.txt` to include `psycopg2-binary>=2.9`

4. Uncomment database code in:
   - `Scan/admin.py`
   - `Scan/views.py` (add model imports and save_to_database calls)

5. Run migrations:
   ```bash
   python manage.py migrate
   ```

## Development

```bash
# Start server
python manage.py runserver

# WebSocket server auto-starts on port 8765
# API available at http://localhost:8000/scan/api/
```

## Requirements

- Python 3.8+
- Serial port access (for BLE scanning)
- No database required
