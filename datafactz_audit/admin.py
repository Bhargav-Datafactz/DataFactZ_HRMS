"""
admin.py
"""

from django.contrib import admin

from datafactz_audit.models import AuditTag, DatafactzAuditInfo, DatafactzAuditLog

# Register your models here.

admin.site.register(AuditTag)
