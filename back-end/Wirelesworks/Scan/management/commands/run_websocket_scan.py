import time

from django.core.management.base import BaseCommand

from Scan.application.background_scan_service import start_background_scanning, stop_background_scanning
from Scan.utils.websocket_server import ws_server


class Command(BaseCommand):
    help = "Start the websocket server and continuous BLE scanning without running Django HTTP endpoints."

    def handle(self, *args, **options):
        del args, options

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting websocket scan service on ws://{ws_server.host}:{ws_server.port}"
            )
        )

        ws_server.start_in_background()

        if not start_background_scanning():
            self.stderr.write(self.style.ERROR("Failed to start background scanning"))
            return

        self.stdout.write(self.style.SUCCESS("Background scanning started"))
        self.stdout.write("Press Ctrl+C to stop")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stdout.write("Stopping websocket scan service...")
            stop_background_scanning()
            self.stdout.write(self.style.SUCCESS("Stopped"))