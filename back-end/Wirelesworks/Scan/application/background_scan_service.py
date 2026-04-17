import os
import re
import threading
import time
from datetime import timedelta

import serial
from django.utils import timezone

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
        self._counter_emit_mode = self._resolve_counter_emit_mode(
            os.environ.get("HOURLY_COUNTER_BROADCAST_EVERY", "hour")
        )
        self._current_hour_start = self._truncate_counter_start(timezone.now())
        self._hourly_unique_devices = set()
        self._hourly_company_unique_devices = {}

    def _resolve_counter_emit_mode(self, mode):
        normalized_mode = str(mode).strip().lower()
        if normalized_mode in {"minute", "hour"}:
            return normalized_mode
        return "hour"

    def _counter_emit_delta(self):
        if self._counter_emit_mode == "minute":
            return timedelta(minutes=1)
        return timedelta(hours=1)

    def _truncate_counter_start(self, dt):
        if self._counter_emit_mode == "minute":
            return dt.replace(second=0, microsecond=0)
        return self._truncate_to_hour(dt)

    def _truncate_to_hour(self, dt):
        return dt.replace(minute=0, second=0, microsecond=0)

    def _build_hourly_total_payload(self, hour_start):
        window_delta = self._counter_emit_delta()
        company_device_counts = {
            company: len(mac_addresses)
            for company, mac_addresses in self._hourly_company_unique_devices.items()
        }
        return {
            "type": "hourly_unique_device_count",
            "hour_start": hour_start.isoformat(),
            "hour_end": (hour_start + window_delta).isoformat(),
            "unique_device_count": len(self._hourly_unique_devices),
            "company_device_counts": company_device_counts,
        }

    def validate_scan_event(self, device_data):
        return bool(device_data)

    def increment_hourly_scan_counter(self, device_data):
        for device_info in device_data.values():
            mac_address = device_info.get("mac")
            if mac_address:
                normalized_mac = str(mac_address).upper()
                self._hourly_unique_devices.add(normalized_mac)

                company_name = device_info.get("company_name")
                if not company_name or company_name == "No Name Found":
                    company_name = "Unknown"
                else:
                    company_name = str(company_name)

                if company_name not in self._hourly_company_unique_devices:
                    self._hourly_company_unique_devices[company_name] = set()
                self._hourly_company_unique_devices[company_name].add(normalized_mac)

    def push_live_device_update(self, device_data):
        self.print_and_broadcast_results(device_data)

    def broadcast_scan_event_to_clients(self, device_data):
        self.push_live_device_update(device_data)

    def process_live_scan_event(self, device_data):
        if not self.validate_scan_event(device_data):
            return False

        self.increment_hourly_scan_counter(device_data)
        self.broadcast_scan_event_to_clients(device_data)
        return True

    def retrieve_and_reset_hourly_counter(self, hour_start):
        total_count = self._build_hourly_total_payload(hour_start)
        self._hourly_unique_devices = set()
        self._hourly_company_unique_devices = {}
        return total_count

    def return_hourly_total(self, total_count):
        ws_server.broadcast_sync(total_count)
        print(
            "🕒 Hourly unique devices "
            f"({total_count['hour_start']} -> {total_count['hour_end']}): "
            f"{total_count['unique_device_count']}"
        )

    def store_hourly_total(self, total_count):
        # Kept as a dedicated step so persistence can move to the data layer.
        print(
            "✓ hourly total ready for persistence: "
            f"{total_count['hour_start']} -> {total_count['hour_end']}"
        )

    def trigger_hourly_persistence(self, now=None):
        now = now or timezone.now()
        emit_delta = self._counter_emit_delta()
        while now >= self._current_hour_start + emit_delta:
            total_count = self.retrieve_and_reset_hourly_counter(self._current_hour_start)
            self.return_hourly_total(total_count)
            self.store_hourly_total(total_count)
            self._current_hour_start += emit_delta

    def _broadcast_hourly_unique_count(self, hour_start):
        self.return_hourly_total(self._build_hourly_total_payload(hour_start))

    def _roll_hour_if_needed(self, now=None):
        self.trigger_hourly_persistence(now=now)

    def _track_hourly_devices(self, devices):
        self.increment_hourly_scan_counter(devices)

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

        header_all = "\n\n\nAll devices\n "
        print(header_all)
        self.push_print_to_websocket(header_all)

        all_devices = list(devices.values())
        for index, device_info in enumerate(all_devices):
            info_string = (
                f"MAC-Address: {device_info.get('mac')} | RSSI: {device_info.get('rssi')} |"
            )

            if device_info.get("company_name") not in [None, "No Name Found"]:
                info_string += f" Company Name: {device_info.get('company_name')}  |"

            if device_info.get("device_name") is not None:
                info_string += f" Device Name: {device_info.get('device_name')}"

            if index == len(all_devices) - 1:
                info_string += "\n"

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
                company_header = f"\nCompany Name: {company}\n"
                print(company_header)
                self.push_print_to_websocket(company_header)
                company_device_list = list(company_devs.values())
                for index, device_info in enumerate(company_device_list):
                    info_string = (
                        f"MAC-Address: {device_info.get('mac')} | RSSI: {device_info.get('rssi')} |"
                    )

                    if device_info.get("company_name") not in [None, "No Name Found"]:
                        info_string += f" Company Name: {device_info.get('company_name')}  |"

                    if device_info.get("device_name") is not None:
                        info_string += f" Device Name: {device_info.get('device_name')}"

                    if index == len(company_device_list) - 1:
                        info_string += "\n"

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
        hour_start = self._current_hour_start.isoformat()
        mode = self._counter_emit_mode
        print(f"hourly counter started on {hour_start} (broadcast every {mode})")
        ws_server.broadcast_sync(
            f"hourly counter started on {hour_start} (broadcast every {mode})"
        )

        while self.running:
            try:
                self.trigger_hourly_persistence()
                devices = self.run_single_scan()
                self.process_live_scan_event(devices)
                self.trigger_hourly_persistence()

                if devices:
                    self.reset()
                else:
                    print("✗ No devices found")
                    ws_server.broadcast_sync("✗ No devices found")

                if self.scan_interval > 0:
                    print(f"⏳ Waiting {self.scan_interval} seconds before next scan...")
                    time.sleep(self.scan_interval)
                    self.trigger_hourly_persistence()
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
