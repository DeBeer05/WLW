# WebSocket Implementatie - Scan.py

## Overzicht
De scan data wordt nu automatisch naar een WebSocket gepushed zodat deze real-time op een website getoond kan worden. Devices worden **live gepushed tijdens het scannen** en aan het einde wordt een samenvatting gestuurd met devices gesorteerd per company.

## Message Types

De WebSocket stuurt 3 verschillende soorten berichten:

### 1. Scan Start
Wordt gestuurd wanneer een scan begint:
```json
{
  "type": "scan_start",
  "timestamp": 1234567890.123,
  "duration": 5
}
```

### 2. Device Found (Real-time)
Wordt gestuurd voor elk device zodra het wordt gevonden en gedecoded:
```json
{
  "type": "device_found",
  "timestamp": 1234567890.123,
  "device": {
    "mac": "AA:BB:CC:DD:EE:FF",
    "rssi": "-65",
    "company_name": "Apple Inc.",
    "device_name": "iPhone"
  }
}
```

### 3. Scan Complete
Wordt gestuurd aan het einde van de scan met een samenvatting:
```json
{
  "type": "scan_complete",
  "timestamp": 1234567890.123,
  "total_devices": 5,
  "devices_by_company": {
    "Apple Inc.": [
      {
        "mac": "AA:BB:CC:DD:EE:FF",
        "rssi": "-65",
        "company_name": "Apple Inc.",
        "device_name": "iPhone"
      }
    ],
    "Samsung": [
      {
        "mac": "11:22:33:44:55:66",
        "rssi": "-70",
        "company_name": "Samsung",
        "device_name": null
      }
    ]
  }
}
```

**Alle JSON berichten zijn mooi geformatteerd met indentation voor betere leesbaarheid.**

## Installatie

1. Installeer de nieuwe dependencies:
```bash
pip install -r requirements.txt
```

Dit installeert de `websockets` library die nodig is voor de WebSocket server.

## Gebruik

### De Scanner Starten

Start de scanner zoals gewoonlijk:
```bash
python Scan.py
```

De WebSocket server start automatisch op `ws://0.0.0.0:8765` en draait in de achtergrond.

### Test Client

Om de WebSocket verbinding te testen, open `websocket_client.html` in een browser. Deze HTML pagina:
- Maakt automatisch verbinding met de WebSocket server
- Toont real-time alle gevonden devices terwijl ze worden gescand
- Toont devices gesorteerd per company wanneer de scan compleet is
- Reconnect automatisch bij verbindingsverlies
- Toont scan status en device counters

## Integratie in Je Website

Om de data in je eigen website te gebruiken:

### JavaScript Voorbeeld

```javascript
const ws = new WebSocket('ws://YOUR_SERVER_IP:8765');
let devices = [];

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case 'scan_start':
            console.log('Starting scan for', data.duration, 'seconds');
            devices = []; // Reset devices list
            break;
            
        case 'device_found':
            console.log('New device found:', data.device);
            devices.push(data.device);
            // Update UI with new device in real-time
            addDeviceToUI(data.device);
            break;
            
        case 'scan_complete':
            console.log('Scan complete! Total:', data.total_devices);
            console.log('By company:', data.devices_by_company);
            // Update company grouped view
            updateCompanyView(data.devices_by_company);
            break;
    }
};

ws.onopen = () => {
    console.log('Connected to scanner');
};

ws.onclose = () => {
    console.log('Disconnected - reconnecting...');
    // Implementeer reconnection logic
};
```

### React Voorbeeld

```javascript
import { useEffect, useState } from 'react';

function ScanMonitor() {
    const [devices, setDevices] = useState([]);
    const [devicesByCompany, setDevicesByCompany] = useState({});
    const [scanning, setScanning] = useState(false);
    const [totalDevices, setTotalDevices] = useState(0);
    
    useEffect(() => {
        const ws = new WebSocket('ws://YOUR_SERVER_IP:8765');
        
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            switch(data.type) {
                case 'scan_start':
                    setScanning(true);
                    setDevices([]);
                    setDevicesByCompany({});
                    break;
                    
                case 'device_found':
                    setDevices(prev => [...prev, data.device]);
                    break;
                    
                case 'scan_complete':
                    setScanning(false);
                    setTotalDevices(data.total_devices);
                    setDevicesByCompany(data.devices_by_company);
                    break;
            }
        };
        
        return () => ws.close();
    }, []);
    
    return (
        <div>
            <h1>BLE Scanner {scanning && '🔍'}</h1>
            
            <h2>All Devices ({devices.length})</h2>
            {devices.map((device, index) => (
                <div key={index}>
                    {device.mac} - {device.company_name || 'Unknown'}
                    {device.device_name && ` (${device.device_name})`}
                </div>
            ))}
            
            <h2>By Company</h2>
            {Object.entries(devicesByCompany).map(([company, devs]) => (
                <div key={company}>
                    <h3>{company} ({devs.length})</h3>
                    {devs.map((device, index) => (
                        <div key={index}>{device.mac}</div>
                    ))}
                </div>
            ))}
        </div>
    );
}
```

## Configuratie

### WebSocket Poort Wijzigen

In `websocket_server.py`, pas de default port aan:

```python
ws_server = WebSocketServer(host="0.0.0.0", port=8765)  # Verander 8765 naar gewenste poort
```

### Host Aanpassen

Standaard luistert de server op `0.0.0.0` (alle interfaces). Voor alleen lokale toegang:

```python
ws_server = WebSocketServer(host="localhost", port=8765)
```

## Troubleshooting

### WebSocket verbindt niet
- Check of port 8765 open is in je firewall
- Controleer of je het juiste IP adres gebruikt
- Kijk in de terminal voor "WebSocket server started" message

### Geen data ontvangen
- Controleer of de scan succesvol loopt
- Check browser console voor errors
- Kijk of je `device_found` messages ontvangt tijdens de scan
- Verify dat `send_to_websocket()` wordt aangeroepen na elke scan

### Connection drops
- De HTML client reconnect automatisch
- Implementeer reconnection logic in je eigen client

## Bestanden

- `websocket_server.py` - WebSocket server implementatie
- `Scan.py` - Aangepast met WebSocket functionaliteit
- `websocket_client.html` - Test client (open in browser)
- `requirements.txt` - Updated met websockets dependency

## Notities

- De WebSocket server draait in een background thread en blokkeert de scanner niet
- **Devices worden real-time gepushed terwijl ze worden gescand** - geen wachten tot de scan compleet is
- Aan het einde van elke scan wordt een samenvatting gestuurd met devices gesorteerd per company
- Meerdere clients kunnen tegelijk verbinden
- De server start automatisch wanneer Scan.py wordt uitgevoerd
- Alle JSON messages zijn mooi geformatteerd met 2-space indentation
