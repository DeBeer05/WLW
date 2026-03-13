import os
import re
import threading
import time

import serial

from Scan.business_logic.bluetooth_scanner import BluetoothScanner
from Scan.utils.websocket_server import ws_server


class ScanService(BluetoothScanner):
    """Application service for continuous BLE scanning and websocket broadcasting."""

    def __init__(
        self,
        port="/dev/ttyS2",
        baudrate=115200,
        timeout=0.2,
        scan_duration=5,
        scan_interval=0,
    ):
        super().__init__(port=port, baudrate=baudrate, timeout=timeout)
        self.scan_duration = scan_duration
        self.scan_interval = scan_interval
        self.running = False
        self.thread = None

    def run_single_scan(self):
        try:
            self.unique_devices = {}
            devices = self.scan(duration=self.scan_duration)
            self.delay()
            print("Scan Completed! Found devices:")
            return devices
        except serial.SerialException as exc:
            print(f"⚠ Serial error during scan: {exc}")
            self.reconnect_serial()
            return {}
        except Exception as exc:
            try:
                self.loading_bar.stop_loading()
            except Exception:
                pass
            print(f"⚠ Scan error: {exc}")
            ws_server.broadcast_sync(f"Scan error: {exc}")
            return {}

    def reconnect_serial(self):
        try:
            print("🔄 Attempting to reconnect serial port...")
            if self.serial_bus and self.serial_bus.is_open:
                self.serial_bus.close()
            time.sleep(2)
            self.configure_serial()
            print("✓ Serial port reconnected")
        except Exception as exc:
            print(f"❌ Failed to reconnect: {exc}")

    def print_and_broadcast_results(self, devices):
        if not devices:
            ws_server.broadcast_sync("No devices found")
            return

        header_all = "\n\n\nAll devices\n"
        print(header_all)
        self.push_print_to_websocket(header_all)

        for device_info in devices.values():
            info_string = (
                f"MAC-Address: {device_info.get('mac')} | RSSI: {device_info.get('rssi')} |"
            )

            if device_info.get("company_name") not in [None, "No Name Found"]:
                info_string += f" Company Name: {device_info.get('company_name')} |"

            if device_info.get("device_name") is not None:
                info_string += f" Device Name: {device_info.get('device_name')}"

            print(info_string)
            self.push_print_to_websocket(info_string)
            self.delay(0.7)

        company_devices = self._sort_by_company(devices)
        self.delay()
        header_company = "\n\n\nDevices sorted by company"
        print(header_company)
        self.push_print_to_websocket(header_company)

        for company, company_devs in company_devices.items():
            if company and company != "No Name Found":
                company_header = f"\nCompany Name: {company}"
                print(company_header)
                self.push_print_to_websocket(company_header)
                for device_info in company_devs.values():
                    info_string = (
                        f"MAC-Address: {device_info.get('mac')} | RSSI: {device_info.get('rssi')} |"
                    )

                    if device_info.get("company_name") not in [None, "No Name Found"]:
                        info_string += f" Company Name: {device_info.get('company_name')} |"

                    if device_info.get("device_name") is not None:
                        info_string += f" Device Name: {device_info.get('device_name')}"

                    print(info_string)
                    self.push_print_to_websocket(info_string)
                    self.delay(0.7)
                self.delay(1)

    def push_print_to_websocket(self, line):
        ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
        cleaned_line = ansi_escape.sub("", line)
        cleaned_line = cleaned_line.lstrip("\n")

        if cleaned_line.strip() == "All devices":
            return
        if cleaned_line.strip() == "":
            return

        ws_server.broadcast_sync(cleaned_line)

    def reset(self):
        self.unique_devices = {}

    def delay(self, seconds=0.1):
        time.sleep(seconds)

    def _sort_by_company(self, devices):
        company_dict = {}
        for mac, device_info in devices.items():
            company = device_info.get("company_name")
            if company and company != "No Name Found":
                if company not in company_dict:
                    company_dict[company] = {}
                company_dict[company][mac] = device_info
        return company_dict

    def run_loop(self):
        print("🔄 Continuous scanning started")
        ws_server.broadcast_sync("🔄 Continuous scanning started")

        while self.running:
            try:
                devices = self.run_single_scan()

                if devices:
                    self.print_and_broadcast_results(devices)
                    self.reset()
                else:
                    print("✗ No devices found")
                    ws_server.broadcast_sync("✗ No devices found")

                if self.scan_interval > 0:
                    print(f"⏳ Waiting {self.scan_interval} seconds before next scan...")
                    time.sleep(self.scan_interval)
            except Exception as exc:
                error_msg = f"⚠ Scan error: {exc}"
                print(error_msg)
                ws_server.broadcast_sync(error_msg)
                time.sleep(self.scan_interval)

    def start(self):
        if self.running:
            print("⚠ Scanning already running")
            return False

        try:
            self.configure_serial()
        except Exception:
            print("❌ Failed to configure serial port")
            return False

        self.running = True
        self.thread = threading.Thread(target=self.run_loop, daemon=True)
        self.thread.start()
        print("✓ Background scanning started")
        return True

    def stop(self):
        self.running = False
        self.close()
        print("✓ Background scanning stopped")


scan_service = None


def start_background_scanning():
    """Initialize and start background scanning service."""
    global scan_service

    port = os.environ.get("SERIAL_PORT", "/dev/ttyS2")
    scan_duration = int(os.environ.get("SCAN_DURATION", "5"))
    scan_interval = int(os.environ.get("SCAN_INTERVAL", "0"))

    scan_service = ScanService(
        port=port,
        scan_duration=scan_duration,
        scan_interval=scan_interval,
    )

    return scan_service.start()


def stop_background_scanning():
    """Stop background scanning service."""
    global scan_service
    if scan_service:
        scan_service.stop()


__all__ = ["ScanService", "start_background_scanning", "stop_background_scanning"]
