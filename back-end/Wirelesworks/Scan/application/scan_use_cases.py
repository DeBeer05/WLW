from Scan.business_logic.bluetooth_scanner import BluetoothScanner
from Scan.data_access.scan_repository import ScanRepository


class ScanUseCases:
    """Application layer orchestration for scan API use-cases."""

    def __init__(self, repository=None):
        self.repository = repository or ScanRepository()

    def start_scan(self, duration=5, port="/dev/ttyS2"):
        scanner = BluetoothScanner(port=port)
        scanner.configure_serial()
        try:
            devices = scanner.scan(duration=duration)
        finally:
            scanner.close()

        session = self.repository.create_scan_session_with_devices(
            duration=duration,
            devices=devices,
        )

        return {
            "status": "success",
            "scan_id": session.id,
            "device_count": len(devices),
            "devices": devices,
        }

    def get_scan_history(self):
        scans = self.repository.get_scan_history()
        return {
            "status": "success",
            "scans": scans,
        }

    def get_scan_details(self, scan_id):
        details = self.repository.get_scan_details(scan_id)
        if details is None:
            return {
                "status": "error",
                "message": "Scan not found.",
            }
        return {"status": "success", "scan": details}

    def index_status(self):
        return {
            "status": "info",
            "message": "Scan API is active. Use /scan/api/start/ to perform scans.",
        }
