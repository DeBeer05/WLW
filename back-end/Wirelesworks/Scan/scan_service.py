import threading
import time
import os
import yaml
import serial
from .utils.loading import Loading
from .utils.websocket_server import ws_server


class ScanService:
    """Background service for continuous BLE scanning"""
    
    def __init__(self, port="/dev/ttyS2", baudrate=115200, timeout=0.2, scan_duration=15, scan_interval=10):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.scan_duration = scan_duration
        self.scan_interval = scan_interval
        self.running = False
        self.thread = None
        self.serial_bus = None
        
        # Load YAML files
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.company_identifiers = self._load_company_dict(
            os.path.join(base_dir, 'yaml_files', 'company_identifiers.yaml')
        )
        self.ad_types = self._load_type_dict(
            os.path.join(base_dir, 'yaml_files', 'ad_types.yaml')
        )
        print(f"📋 Loaded {len(self.company_identifiers)} company identifiers from YAML")
    
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
        try:
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
            return True
        except Exception as e:
            print(f"⚠ Failed to configure serial: {e}")
            return False
    
    def scan(self):
        """Perform single Bluetooth scan"""
        unique_devices = {}
        
        try:
            self.serial_bus.flushInput()
            ignore_list = ['', '\n']
            
            command = f'AT+LSCN {self.scan_duration}\r'.encode()
            self.serial_bus.write(command)
            
            ok_reached = False
            
            while not ok_reached:
                device = {}
                try:
                    incoming_adv = self.serial_bus.readline().decode()
                except serial.SerialException as se:
                    print(f"⚠ Serial error during scan: {str(se)}")
                    # Try to recover the connection
                    self.reconnect_serial()
                    return unique_devices
                
                if len(incoming_adv) > 28:
                    device['mac'] = incoming_adv[6:20]
                    device['rssi'] = incoming_adv[21:24]
                    device['data'] = incoming_adv[26:-2]
                    
                    if device['data'][-1] == '"':
                        device['data'] = incoming_adv[26:-3]
                    
                    unique_devices[device['mac']] = device
                    self._decode_advert(unique_devices[device['mac']])
                elif incoming_adv not in ignore_list:
                    ok_reached = True
            
            return unique_devices
        except Exception as e:
            print(f"⚠ Scan error: {str(e)}")
            ws_server.broadcast_sync(f"Scan error: {str(e)}")
            return {}
    
    def reconnect_serial(self):
        """Attempt to reconnect the serial port"""
        try:
            print("🔄 Attempting to reconnect serial port...")
            if self.serial_bus and self.serial_bus.is_open:
                self.serial_bus.close()
            time.sleep(2)
            self.configure_serial()
            print("✓ Serial port reconnected")
        except Exception as e:
            print(f"❌ Failed to reconnect: {str(e)}")

    
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
        try:
            # Remove common prefixes/spaces and strip
            company_id = company_id.strip().replace(' ', '').replace('0x', '')
            
            # Take first 4 characters (2 bytes = 4 hex chars)
            if len(company_id) >= 4:
                company_id = company_id[:4]
            else:
                company_id = company_id.zfill(4)
            
            # Byte swap: Little Endian to Big Endian
            byte1 = company_id[:2]
            byte2 = company_id[2:4]
            company_id_rotated = byte2 + byte1
            
            # Try different key variations (the YAML keys are uppercase)
            for key_attempt in [
                company_id_rotated.upper(),  # Swapped + uppercase
                company_id_rotated.lower(),  # Swapped + lowercase
                company_id.upper(),           # Not swapped + uppercase
                company_id.lower()            # Not swapped + lowercase
            ]:
                if key_attempt in self.company_identifiers:
                    device['company_name'] = self.company_identifiers[key_attempt]
                    return
            
            # If no match found, set to "Unknown" 
            device['company_name'] = "Unknown"
        except Exception as e:
            device['company_name'] = "Unknown"
    
    def _get_device_name(self, device, hex_name):
        """Extract device name"""
        try:
            name = bytes.fromhex(hex_name.replace('\0', '')).decode()
            device['device_name'] = name
            
            if "PNL" in name.upper():
                device['company_name'] = "PNL"
            if "LAIRD" in name.upper():
                device['company_name'] = "Laird"
        except:
            pass
    
    def print_and_broadcast_results(self, devices):
        """Print results and broadcast via WebSocket"""
        if not devices:
            ws_server.broadcast_sync("No devices found")
            return
        
        # All devices
        header = f"\n=== All Devices ({len(devices)}) ===\n"
        print(header)
        ws_server.broadcast_sync(header)
        
        for mac, device_info in devices.items():
            info_string = f"{device_info.get('mac')} | RSSI: {device_info.get('rssi')} | " \
                         f"Company: {device_info.get('company_name', 'Unknown')} | " \
                         f"Name: {device_info.get('device_name', 'N/A')}"
            print(info_string)
            ws_server.broadcast_sync(info_string)
            time.sleep(1)  # Delay between each device
        
        # Devices by company
        company_devices = self._sort_by_company(devices)
        
        header_company = "\n=== Devices Sorted by Company ===\n"
        print(header_company)
        ws_server.broadcast_sync(header_company)
        
        for company, company_devs in company_devices.items():
            company_header = f"\n{company}:"
            print(company_header)
            ws_server.broadcast_sync(company_header)
            
            for mac, device_info in company_devs.items():
                info_string = f"  {device_info.get('mac')} | RSSI: {device_info.get('rssi')} | " \
                             f"Name: {device_info.get('device_name', 'N/A')}"
                print(info_string)
                ws_server.broadcast_sync(info_string)
                time.sleep(1)  # Delay between each device
    
    def _sort_by_company(self, devices):
        """Sort devices by company name"""
        company_dict = {}
        for mac, device_info in devices.items():
            company = device_info.get('company_name')
            if company and company != 'No Name Found':
                if company not in company_dict:
                    company_dict[company] = {}
                company_dict[company][mac] = device_info
        return company_dict
    
    def run_loop(self):
        """Background scanning loop"""
        print("🔄 Continuous scanning started")
        ws_server.broadcast_sync("🔄 Continuous scanning started")
        
        while self.running:
            try:
               
                
                devices = self.scan()
                
                if devices:
                    
                    
                    self.print_and_broadcast_results(devices)
                else:
                    print("✗ No devices found")
                    ws_server.broadcast_sync("✗ No devices found")
                
                # Wait before next scan
                print(f"⏳ Waiting {self.scan_interval} seconds before next scan...")
                time.sleep(self.scan_interval)
                
            except Exception as e:
                error_msg = f"⚠ Scan error: {str(e)}"
                print(error_msg)
                ws_server.broadcast_sync(error_msg)
                time.sleep(self.scan_interval)
    
    def start(self):
        """Start background scanning"""
        if self.running:
            print("⚠ Scanning already running")
            return False
        
        if not self.configure_serial():
            print("❌ Failed to configure serial port")
            return False
        
        self.running = True
        self.thread = threading.Thread(target=self.run_loop, daemon=True)
        self.thread.start()
        print("✓ Background scanning started")
        return True
    
    def stop(self):
        """Stop background scanning"""
        self.running = False
        if self.serial_bus and self.serial_bus.is_open:
            self.serial_bus.close()
        print("✓ Background scanning stopped")


# Global instance
scan_service = None

def start_background_scanning():
    """Initialize and start background scanning service"""
    global scan_service
    
    # Get configuration from environment or use defaults
    port = os.environ.get('SERIAL_PORT', '/dev/ttyS2')
    scan_duration = int(os.environ.get('SCAN_DURATION', '5'))
    scan_interval = int(os.environ.get('SCAN_INTERVAL', '10'))
    
    scan_service = ScanService(
        port=port,
        scan_duration=scan_duration,
        scan_interval=scan_interval
    )
    
    return scan_service.start()

def stop_background_scanning():
    """Stop background scanning service"""
    global scan_service
    if scan_service:
        scan_service.stop()
