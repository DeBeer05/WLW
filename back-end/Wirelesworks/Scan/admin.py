from django.contrib import admin

# Database disabled - admin functionality not available

"""
# These models are available but database is disabled
# Uncomment when database is enabled

from .models import ScanSession, Device


class DeviceInline(admin.TabularInline):
    model = Device
    extra = 0
    fields = ('mac_address', 'rssi', 'company_name', 'device_name')
    readonly_fields = ('mac_address', 'rssi', 'company_name', 'device_name')


@admin.register(ScanSession)
class ScanSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'timestamp', 'duration', 'device_count')
    list_filter = ('timestamp',)
    readonly_fields = ('timestamp', 'device_count')
    inlines = [DeviceInline]


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('mac_address', 'company_name', 'device_name', 'rssi', 'scan_session')
    list_filter = ('company_name', 'scan_session__timestamp')
    search_fields = ('mac_address', 'company_name', 'device_name')
    readonly_fields = ('decoded_data',)
"""
