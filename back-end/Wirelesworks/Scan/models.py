from django.db import models
from django.utils import timezone


class ScanSession(models.Model):
    """Represents a scanning session"""
    timestamp = models.DateTimeField(default=timezone.now)
    duration = models.IntegerField(help_text="Scan duration in seconds")
    device_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Scan at {self.timestamp} - {self.device_count} devices"


class Device(models.Model):
    """Represents a Bluetooth device found during scanning"""
    scan_session = models.ForeignKey(ScanSession, on_delete=models.CASCADE, related_name='devices')
    mac_address = models.CharField(max_length=20, db_index=True)
    rssi = models.CharField(max_length=10)
    raw_data = models.TextField()
    company_name = models.CharField(max_length=255, blank=True, null=True)
    device_name = models.CharField(max_length=255, blank=True, null=True)
    decoded_data = models.JSONField(blank=True, null=True)
    
    class Meta:
        ordering = ['mac_address']
        
    def __str__(self):
        return f"{self.mac_address} - {self.company_name or 'Unknown'}"
