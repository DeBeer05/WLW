from django.apps import AppConfig


class ScanConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Scan'

    def ready(self):
        """Initialize the app - start websocket server and background scanning"""
        import os
        # Only start once (Django runs ready() twice in some cases)
        if os.environ.get('RUN_MAIN') == 'true':
            try:
                from .utils.websocket_server import ws_server
                ws_server.start_in_background()
                print("✓ WebSocket server started automatically")
            except Exception as e:
                print(f"⚠ WebSocket server failed to start: {e}")
            
            try:
                from .scan_service import start_background_scanning
                start_background_scanning()
            except Exception as e:
                print(f"⚠ Background scanning failed to start: {e}")
