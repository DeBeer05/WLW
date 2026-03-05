# Scan Django App

A compact Django application for Bluetooth Low Energy (BLE) device scanning integrated with WebSocket support.

## Structure

```
Scan/
├── models.py           # Django models for ScanSession and Device
├── views.py            # API endpoints and BluetoothScanner class
├── admin.py            # Django admin configuration
├── urls.py             # URL routing
├── utils/              # Utility modules
│   ├── websocket_server.py
│   └── loading.py
├── yaml_files/         # Configuration files
│   ├── company_identifiers.yaml
│   └── ad_types.yaml
└── migrations/         # Database migrations
```

## API Endpoints

### Start Scan
```
POST /scan/api/start/
Body: {
    "duration": 5,      // Scan duration in seconds (optional, default: 5)
    "port": "/dev/ttyS2" // Serial port (optional, default: /dev/ttyS2)
}
```

### Get Scan History
```
GET /scan/api/history/
Returns: List of last 10 scan sessions
```

### Get Scan Details
```
GET /scan/api/details/<scan_id>/
Returns: Detailed information about a specific scan including all devices
```

### Dashboard
```
GET /scan/
Returns: HTML dashboard with recent scans
```

## Setup

1. Run migrations:
```bash
python manage.py makemigrations
python manage.py migrate
```

2. Create superuser (optional, for admin access):
```bash
python manage.py createsuperuser
```

3. Start development server:
```bash
python manage.py runserver
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

# Get scan history
history = requests.get('http://localhost:8000/scan/api/history/').json()
```

### Via Django Admin
1. Access admin panel at http://localhost:8000/admin/
2. View and manage scan sessions and devices
3. Filter by company name, timestamp, etc.

## Models

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

- WebSocket server runs in the background for real-time updates
- All scan results are automatically saved to the database
- YAML files contain company identifiers and advertisement type definitions
