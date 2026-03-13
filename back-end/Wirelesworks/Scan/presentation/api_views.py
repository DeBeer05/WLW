import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from Scan.application.scan_use_cases import ScanUseCases


scan_use_cases = ScanUseCases()


@csrf_exempt
@require_http_methods(["POST"])
def start_scan(request):
    try:
        data = json.loads(request.body) if request.body else {}
        duration = data.get("duration", 5)
        port = data.get("port", "/dev/ttyS2")
        payload = scan_use_cases.start_scan(duration=duration, port=port)
        return JsonResponse(payload)
    except Exception as exc:
        return JsonResponse({"status": "error", "message": str(exc)}, status=500)


@require_http_methods(["GET"])
def get_scan_history(request):
    _ = request
    return JsonResponse(scan_use_cases.get_scan_history())


@require_http_methods(["GET"])
def get_scan_details(request, scan_id):
    _ = request
    return JsonResponse(scan_use_cases.get_scan_details(scan_id=scan_id))


@require_http_methods(["GET"])
def index(request):
    _ = request
    return JsonResponse(scan_use_cases.index_status())
