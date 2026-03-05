# WirelesWorks - Smart IoT Gateway Scan

Django-based Bluetooth Low Energy (BLE) scanning system with real-time WebSocket updates.

⚠️ **Database is disabled** - All database functionality has been turned off. Scan data is not persisted.

## Quick Start

```bash
cd back-end/Wirelesworks

# Install dependencies (no database packages needed)
pip install -r requirements.txt

# Start server (WebSocket auto-starts)
python manage.py runserver
```

Access API at: `http://localhost:8000/scan/api/start/`

## Project Structure

```
WLW/
├── back-end/
│   └── Wirelesworks/      # Django backend
│       ├── Scan/          # BLE scanning app
│       ├── requirements.txt
│       └── README.md
├── img/                   # Project diagrams and images
└── README.md
```

## Features

- ✅ BLE device scanning via serial communication
- ✅ Company identifier decoding
- ✅ Device name extraction
- ✅ Real-time WebSocket updates
- ✅ REST API endpoints
- ✅ Automatic WebSocket server startup
- ❌ **Database disabled (no persistence)**
- ❌ **Admin panel disabled**

## API Endpoints

- `POST /scan/api/start/` - Start a BLE scan
- `GET /scan/api/history/` - (disabled)
- `GET /scan/api/details/<id>/` - (disabled)
- `GET /scan/` - Info

## Documentation

- [Backend README](back-end/Wirelesworks/README.md) - Backend documentation
- [Installation Guide](back-end/Wirelesworks/INSTALLATION.md) - Detailed setup (database re-enable info)

## Development Log

### 19-02-26
1. Made github for my end internship. My contract, work plan and work planning are in there.
2. Added my first sequence diagram in the img folder and edited the overall format of my werkhandleiding.
3. Made more sequence diagrams, there are now 3 total. First we have a diagram for how the live scan will be shown - [sequence_diagram_Smart-Iot-Gateway-Scan moderniseren.png](img/sequence_diagram_Smart-Iot-Gateway-Scan%20moderniseren.png) and another one to show how the data for the grafiek will be gotten - [sequence_diagram_Grafiek_Smart-IoT-Gateway-Scan.png](img/sequence_diagram_Grafiek_Smart-IoT-Gateway-Scan.png) and one to show the overall process [diagram](img/TPJFYjim4CRlWRo3oCbxs1TOI5d_ITa5TqcRb5vwKQHfBEf8PYIPvkqx8oMECUqb6FIRRxxvHigh3n93lFJhbLJ1eTXKVOJWNEZ4GKahzkWKU2-A-alpj17IYqDTVapqPtGsWDMYxWtOa82wVTzz72VapKNihwJMWOuzu4taRTUiL-lLGEsDCeEqGMps29vKP33EY.png)
4. Made powerpoint to show and tell what i want to build.
5. Made back-end in Django for project start. Wirelesworks is the project root and Scan is the app.
6. Integrated scanning functionality into Django, migrated to PostgreSQL database.
7. **Disabled all database functionality** - No persistence, no admin panel.

## Image links

- [sequence_diagram_Grafiek_Smart-IoT-Gateway-Scan.png](img/sequence_diagram_Grafiek_Smart-IoT-Gateway-Scan.png)
- [sequence_diagram_Smart-Iot-Gateway-Scan moderniseren.png](img/sequence_diagram_Smart-Iot-Gateway-Scan%20moderniseren.png)
- [diagram](img/TPJFYjim4CRlWRo3oCbxs1TOI5d_ITa5TqcRb5vwKQHfBEf8PYIPvkqx8oMECUqb6FIRRxxvHigh3n93lFJhbLJ1eTXKVOJWNEZ4GKahzkWKU2-A-alpj17IYqDTVapqPtGsWDMYxWtOa82wVTzz72VapKNihwJMWOuzu4taRTUiL-lLGEsDCeEqGMps29vKP33EY.png)
- [wirelessworks-embed.webp](img/wirelessworks-embed.webp)

## Requirements

- Python 3.8+
- Serial port access (for BLE hardware communication)
- ~~PostgreSQL 12+~~ (database disabled)