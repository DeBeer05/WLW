"""Backward-compatible scan service imports.

Use Scan.application.background_scan_service for new code.
"""

from Scan.application.background_scan_service import (
    ScanService,
    start_background_scanning,
    stop_background_scanning,
)

__all__ = ["ScanService", "start_background_scanning", "stop_background_scanning"]
