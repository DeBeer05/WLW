"""Backward-compatible view exports.

Routes still import from this module, but implementations live in Scan.presentation.
"""

from Scan.presentation.api_views import get_scan_details, get_scan_history, index, start_scan

__all__ = ["start_scan", "get_scan_history", "get_scan_details", "index"]
