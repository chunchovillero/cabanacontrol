from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    tenant = models.ForeignKey("tenants.Tenant", null=True, on_delete=models.PROTECT)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    entity = models.CharField(max_length=40)
    entity_id = models.CharField(max_length=64, blank=True)
    action = models.CharField(max_length=50)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["tenant", "timestamp"])]
