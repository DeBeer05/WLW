# Scan Django App

A compact Django application for Bluetooth Low Energy (BLE) device scanning integrated with WebSocket support.

⚠️ **Database is disabled** - Scan results are not persisted. Data is lost when the application stops.

## Structure

```
Scan/
├── models.py           # Django models (not used, DB disabled)
├── views.py            # API endpoints and BluetoothScanner class
├── admin.py            # Django admin (disabled)
├── urls.py             # URL routing
├── utils/              # Utility modules
│   ├── websocket_server.py
│   └── loading.py
├── yaml_files/         # Configuration files
│   ├── company_identifiers.yaml
│   └── ad_types.yaml
└── migrations/         # Database migrations (not used)
```

## API Endpoints

### Start Scan
```
POST /scan/api/start/
Body: {
    "duration": 5,      // Scan duration in seconds (optional, default: 5)
    "port": "/dev/ttyS2" // Serial port (optional, default: /dev/ttyS2)
}
Response: {
    "status": "success",
    "device_count": 5,
    "devices": { ... }
}
```

### Get Scan History
```
GET /scan/api/history/
Response: Database disabled info
```

### Get Scan Details
```
GET /scan/api/details/<scan_id>/
Response: Database disabled info
```

### Dashboard
```
GET /scan/
Response: Info message
```

## Setup

**⚠️ Database is disabled** - No migrations or database setup required.

1. Install dependencies:
```bash
cd back-end/Wirelesworks
pip install -r requirements.txt
```

2. Start development server:
```bash
python manage.py runserver
```

The WebSocket server starts automatically. You'll see:
```
✓ WebSocket server started automatically
```

## Usage

### Via API
```python
import requests

# Start a scan
response = requests.post('http://localhost:8000/scan/api/start/', 
                        json={'duration': 10})
result = response.json()
print(f"Found {result['device_count']} devices")

for mac, device_info in result['devices'].items():
    print(f"{mac}: {device_info.get('company_name', 'Unknown')}")
```

### Via WebSocket
The WebSocket server broadcasts scan results in real-time on port 8765.

## Models

Models are defined but **not used** (database disabled):

### ScanSession
- timestamp: When the scan was performed
- duration: Scan duration in seconds
- device_count: Number of devices found

### Device
- mac_address: Device MAC address
- rssi: Signal strength
- company_name: Decoded company name
- device_name: Device name (if available)
- decoded_data: Full decoded advertisement data (JSON)

## Notes

- ⚠️ **Database disabled** - Scan results are NOT persisted
- ⚠️ **Admin panel disabled** - No Django admin access
- ✅ WebSocket server auto-starts when Django runs (port 8765)
- ✅ YAML files contain company identifiers and advertisement type definitions
- ✅ No database dependencies or migrations required

## Re-enabling Database

To re-enable PostgreSQL database functionality, see [README.md](../README.md) "Enabling Database" section.

## Requirements

- Python 3.8+
- Serial port access (for BLE hardware)
- No database required
