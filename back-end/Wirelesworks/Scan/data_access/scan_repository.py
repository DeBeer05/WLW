from django.db import transaction

from Scan.models import Device, ScanSession


class ScanRepository:
    """Data access abstraction for scan persistence and retrieval."""

    @transaction.atomic
    def create_scan_session_with_devices(self, duration, devices):
        session = ScanSession.objects.create(
            duration=int(duration),
            device_count=len(devices),
        )

        device_rows = []
        for device in devices.values():
            device_rows.append(
                Device(
                    scan_session=session,
                    mac_address=device.get("mac", ""),
                    rssi=str(device.get("rssi", "")),
                    raw_data=device.get("data", ""),
                    company_name=device.get("company_name"),
                    device_name=device.get("device_name"),
                    decoded_data=device.get("sep_data"),
                )
            )

        if device_rows:
            Device.objects.bulk_create(device_rows)

        return session

    def get_scan_history(self, limit=50):
        scans = (
            ScanSession.objects.all()
            .order_by("-timestamp")[:limit]
        )
        return [
            {
                "id": scan.id,
                "timestamp": scan.timestamp.isoformat(),
                "duration": scan.duration,
                "device_count": scan.device_count,
            }
            for scan in scans
        ]

    def get_scan_details(self, scan_id):
        scan = (
            ScanSession.objects.filter(id=scan_id)
            .prefetch_related("devices")
            .first()
        )
        if scan is None:
            return None

        return {
            "id": scan.id,
            "timestamp": scan.timestamp.isoformat(),
            "duration": scan.duration,
            "device_count": scan.device_count,
            "devices": [
                {
                    "id": device.id,
                    "mac": device.mac_address,
                    "rssi": device.rssi,
                    "data": device.raw_data,
                    "company_name": device.company_name,
                    "device_name": device.device_name,
                    "sep_data": device.decoded_data,
                }
                for device in scan.devices.all().order_by("mac_address")
            ],
        }
