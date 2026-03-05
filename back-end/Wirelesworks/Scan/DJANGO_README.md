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

**Note:** Automatic scanning runs continuously in the background. These endpoints are for manual control.

### Start Manual Scan
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

**Automatic scanning starts immediately!** You'll see:
```
✓ WebSocket server started automatically
✓ Background scanning started

▶ Scanning for 5 seconds...
✓ Found 3 device(s)
...
```

Results are broadcast live via WebSocket and printed to console.

## Configuration

Configure scanning behavior via environment variables:

```bash
# Set serial port (default: /dev/ttyS2)
export SERIAL_PORT=/dev/ttyUSB0

# Set scan duration in seconds (default: 5)
export SCAN_DURATION=10

# Set interval between scans in seconds (default: 10)
export SCAN_INTERVAL=15

# Then start server
python manage.py runserver
```

Or create a `.env` file in the project directory and load it:
```bash
export SERIAL_PORT=/dev/ttyUSB0
export SCAN_DURATION=10
export SCAN_INTERVAL=15
python manage.py runserver
```

## Usage

### Automatic Scanning (Continuous Background)

When you start the server, scanning automatically begins:

1. **Console Output:**
```
▶ Scanning for 5 seconds...
✓ Found 3 device(s)
AA:BB:CC:DD:EE:FF | RSSI: -45 | Company: Apple | Name: iPhone
...
⏳ Waiting 10 seconds before next scan...
```

2. **WebSocket Broadcast:**
Connect to `ws://localhost:8765` to receive real-time scan results:
```python
import asyncio
import websockets

async def listen_scans():
    async with websockets.connect('ws://localhost:8765') as ws:
        while True:
            data = await ws.recv()
            print(f"Scan update: {data}")

asyncio.run(listen_scans())
```

### Manual Scanning (API Endpoint)

Trigger a scan via the API:
```python
import requests

response = requests.post('http://localhost:8000/scan/api/start/', 
                        json={'duration': 10})
result = response.json()
print(f"Found {result['device_count']} devices")
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

- ✅ **Automatic Continuous Scanning** - Starts when server starts
- ✅ **Real-time WebSocket Broadcasts** - Results sent to all connected clients
- ✅ **Configurable via Environment** - SERIAL_PORT, SCAN_DURATION, SCAN_INTERVAL
- ⚠️ **Database disabled** - Scan results are NOT persisted
- ⚠️ **Admin panel disabled** - No Django admin access
- ✅ **No database dependencies** - PostgreSQL not required

## Environment Variables

Configure the scanner behavior:

```bash
# Serial port to use (default: /dev/ttyS2)
SERIAL_PORT=/dev/ttyUSB0

# Duration of each scan in seconds (default: 5)
SCAN_DURATION=10

# Interval between scans in seconds (default: 10)
SCAN_INTERVAL=15
```

Example with all options:
```bash
export SERIAL_PORT=/dev/ttyUSB0
export SCAN_DURATION=15
export SCAN_INTERVAL=20
python manage.py runserver
```

## Re-enabling Database

To re-enable PostgreSQL database functionality, see [README.md](../README.md) "Enabling Database" section.

## Requirements

- Python 3.8+
- Serial port access (for BLE hardware)
- No database required
