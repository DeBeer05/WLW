import threading
import time
import os
import re
import yaml
import serial
from .utils.loading import Loading
from .utils.websocket_server import ws_server


class ScanService:
    """Background service for continuous BLE scanning"""
    
    def __init__(
        self,
        port="/dev/ttyS2",
        baudrate=115200,
        timeout=0.2,
        scan_duration=5,
        scan_interval=0,
    ):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.scan_duration = scan_duration
        self.scan_interval = scan_interval
        self.running = False
        self.thread = None
        self.serial_bus = None
        self.unique_devices = {}
        self.loading_bar = Loading("Scanning")
        
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
        try:
            self.unique_devices = {}
            self.serial_bus.flushInput()
            ignore_list = ['', '\n']
            
            command = f'AT+LSCN {self.scan_duration}\r'.encode()
            self.serial_bus.write(command)
            self.loading_bar.start_loading()
            
            ok_reached = False
            
            while not ok_reached:
                device = {}
                try:
                    incoming_adv = self.serial_bus.readline().decode()
                except serial.SerialException as se:
                    print(f"⚠ Serial error during scan: {str(se)}")
                    # Try to recover the connection
                    self.reconnect_serial()
                    self.loading_bar.stop_loading()
                    return {}
                
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
            self.delay()
            print("Scan Completed! Found devices:")
            return self.unique_devices
        except Exception as e:
            try:
                self.loading_bar.stop_loading()
            except Exception:
                pass
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
            company_id = str(company_id)
            byte1 = company_id[:2]
            byte2 = company_id[2:4]
            company_id_rotated = byte2 + byte1

            comp_name = self.company_identifiers.get(str(company_id_rotated))
            if comp_name:
                device['company_name'] = comp_name
            else:
                device['company_name'] = "No Name Found"
        except Exception:
            device['company_name'] = "No Name Found"
    
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
        """Print results and broadcast via WebSocket, matching original scan script formatting."""
        if not devices:
            ws_server.broadcast_sync("No devices found")
            return
        
        header_all = '\n\n\nAll devices\n'
        print(header_all)
        self.push_print_to_websocket(header_all)
        
        for mac, device_info in devices.items():
            info_string = f"MAC-Address: {device_info.get('mac')} | RSSI: {device_info.get('rssi')} |"

            if device_info.get('company_name') not in [None, 'No Name Found']:
                info_string += f" Company Name: {device_info.get('company_name')} |"

            if device_info.get('device_name') is not None:
                info_string += f" Device Name: {device_info.get('device_name')}"

            print(info_string)
            self.push_print_to_websocket(info_string)
            self.delay(0.7)
        
        company_devices = self._sort_by_company(devices)
        self.delay()
        header_company = '\n\n\nDevices sorted by company'
        print(header_company)
        self.push_print_to_websocket(header_company)
        
        for company, company_devs in company_devices.items():
            if company and company != 'No Name Found':
                company_header = f"\nCompany Name: {company}"
                print(company_header)
                self.push_print_to_websocket(company_header)
                for mac, device_info in company_devs.items():
                    info_string = f"MAC-Address: {device_info.get('mac')} | RSSI: {device_info.get('rssi')} |"

                    if device_info.get('company_name') not in [None, 'No Name Found']:
                        info_string += f" Company Name: {device_info.get('company_name')} |"

                    if device_info.get('device_name') is not None:
                        info_string += f" Device Name: {device_info.get('device_name')}"

                    print(info_string)
                    self.push_print_to_websocket(info_string)
                    self.delay(0.7)
                self.delay(1)

    def push_print_to_websocket(self, line):
        ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
        cleaned_line = ansi_escape.sub('', line)
        cleaned_line = cleaned_line.lstrip('\n')

        if cleaned_line.strip() == 'All devices':
            return
        if cleaned_line.strip() == '':
            return

        ws_server.broadcast_sync(cleaned_line)

    def reset(self):
        self.unique_devices = {}

    def delay(self, n=0.1):
        time.sleep(n)
    
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
                    self.reset()
                else:
                    print("✗ No devices found")
                    ws_server.broadcast_sync("✗ No devices found")
                
                # Wait before next scan
                if self.scan_interval > 0:
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
    scan_interval = int(os.environ.get('SCAN_INTERVAL', '0'))
    
    scan_service = ScanService(
        port=port,
        scan_duration=scan_duration,
        scan_interval=scan_interval,
    )
    
    return scan_service.start()

def stop_background_scanning():
    """Stop background scanning service"""
    global scan_service
    if scan_service:
        scan_service.stop()
