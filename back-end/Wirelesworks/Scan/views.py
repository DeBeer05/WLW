from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import serial
import time
import yaml
import json
import re
import os
from .utils.loading import Loading
from .utils.websocket_server import ws_server


class BluetoothScanner:
    """Main Bluetooth scanning class integrated with Django"""
    
    def __init__(self, port="/dev/ttyS2", baudrate=115200, timeout=0.2):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.unique_devices = {}
        self.serial_bus = None
        
        # Load YAML files
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.company_identifiers = self._load_company_dict(
            os.path.join(base_dir, 'yaml_files', 'company_identifiers.yaml')
        )
        self.ad_types = self._load_type_dict(
            os.path.join(base_dir, 'yaml_files', 'ad_types.yaml')
        )
        self.loading_bar = Loading("Scanning")
    
    def _load_company_dict(self, file_path):
        """Load company identifiers from YAML"""
        yaml_dict = {}
        with open(file_path, 'r') as file:
            yaml_contents = yaml.load(file, Loader=yaml.BaseLoader)
        for company in yaml_contents['company_identifiers']:
            yaml_dict[company['value']] = company['name']
        return yaml_dict
    
    def _load_type_dict(self, file_path):
        """Load advertisement types from YAML"""
        yaml_dict = {}
        with open(file_path, 'r') as file:
            yaml_contents = yaml.safe_load(file)
        for types in yaml_contents['ad_types']:
            yaml_dict[str(types['value']).zfill(2)] = types['name']
        return yaml_dict
    
    def configure_serial(self):
        """Configure serial connection"""
        self.serial_bus = serial.Serial(port=self.port, baudrate=self.baudrate, timeout=self.timeout)
        if self.serial_bus.is_open:
            self.serial_bus.close()
        self.serial_bus.open()
        self.serial_bus.send_break(0.1)
        time.sleep(3)
        self.serial_bus.write('AT+SFMT 1\r'.encode())
        time.sleep(3)
        self.serial_bus.flushInput()
        self.serial_bus.flushOutput()
        time.sleep(3)
    
    def scan(self, duration=5):
        """Perform Bluetooth scan"""
        self.serial_bus.flushInput()
        ignore_list = ['', '\n']
        
        command = f'AT+LSCN {duration}\r'.encode()
        self.serial_bus.write(command)
        
        self.loading_bar.start_loading()
        ok_reached = False
        
        while not ok_reached:
            device = {}
            incoming_adv = self.serial_bus.readline().decode()
            
            if len(incoming_adv) > 28:
                device['mac'] = incoming_adv[6:20]
                device['rssi'] = incoming_adv[21:24]
                device['data'] = incoming_adv[26:-2]
                
                if device['data'][-1] == '"':
                    device['data'] = incoming_adv[26:-3]
                
                self.unique_devices[device['mac']] = device
                self._decode_advert(self.unique_devices[device['mac']])
            elif incoming_adv not in ignore_list:
                ok_reached = True
        
        self.loading_bar.stop_loading()
        time.sleep(0.1)
        return self.unique_devices
    
    def _decode_advert(self, device):
        """Decode advertisement data"""
        offset = 2
        data = device.get('data')
        
        if data:
            device['sep_data'] = {}
            while offset < len(data):
                data_len = int(data[offset - 2: offset], 16) * 2
                data_type = data[offset: offset + 2]
                data_data = data[offset + 2: offset + data_len]
                
                if data_type == 'FF':  # Company data
                    device['sep_data'][data_type] = {
                        'data_len': data_len,
                        'data_type': data_type,
                        'data_type_str': self.ad_types.get(data_type),
                        'data': data_data
                    }
                    self._get_company_name(device, data_data)
                elif data_type in ['08', '09']:  # Device name
                    device['sep_data'][data_type] = {
                        'data_len': data_len,
                        'data_type': data_type,
                        'data_type_str': self.ad_types.get(data_type),
                        'data': data_data
                    }
                    self._get_device_name(device, data_data)
                else:
                    device['sep_data'][data_type] = {
                        'data_len': data_len,
                        'data_type': data_type,
                        'data_type_str': self.ad_types.get(data_type),
                        'data': data_data
                    }
                offset += data_len + 2
    
    def _get_company_name(self, device, company_id):
        """Extract company name from identifier"""
        byte1 = company_id[:2]
        byte2 = company_id[2:4]
        company_id_rotated = byte2 + byte1
        comp_name = self.company_identifiers.get(str(company_id_rotated))
        device['company_name'] = comp_name if comp_name else "No Name Found"
    
    def _get_device_name(self, device, hex_name):
        """Extract device name"""
        name = bytes.fromhex(hex_name.replace('\0', '')).decode()
        device['device_name'] = name
        
        if "PNL" in name.upper():
            device['company_name'] = "PNL"
        if "LAIRD" in name.upper():
            device['company_name'] = "Laird"
    
    def close(self):
        """Close serial connection"""
        if self.serial_bus and self.serial_bus.is_open:
            self.serial_bus.close()


# Django Views
@csrf_exempt
@require_http_methods(["POST"])
def start_scan(request):
    """API endpoint to start a Bluetooth scan"""
    try:
        data = json.loads(request.body) if request.body else {}
        duration = data.get('duration', 5)
        port = data.get('port', '/dev/ttyS2')
        
        scanner = BluetoothScanner(port=port)
        scanner.configure_serial()
        devices = scanner.scan(duration=duration)
        scanner.close()
        
        return JsonResponse({
            'status': 'success',
            'device_count': len(devices),
            'devices': devices
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@require_http_methods(["GET"])
def get_scan_history(request):
    """Get scan history (in-memory only, no database)"""
    return JsonResponse({
        'status': 'info',
        'message': 'Database disabled. Scan data is not persisted.',
        'scans': []
    })


@require_http_methods(["GET"])
def get_scan_details(request, scan_id):
    """Get scan details (database disabled)"""
    return JsonResponse({
        'status': 'info',
        'message': 'Database disabled. Scan details not available.',
    })


def index(request):
    """Main dashboard view (no database)"""
    return JsonResponse({
        'status': 'info',
        'message': 'Database disabled. Use /scan/api/start/ to perform scans.',
    })
