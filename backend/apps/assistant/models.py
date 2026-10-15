from django.db import models


class TenantAISettings(models.Model):
    tenant = models.OneToOneField("tenants.Tenant", on_delete=models.PROTECT, primary_key=True)
    enabled = models.BooleanField(default=False)
    voice_enabled = models.BooleanField(default=False)
    daily_requests = models.PositiveIntegerField(default=50)
    daily_tokens = models.PositiveIntegerField(default=100000)
    daily_audio_seconds = models.PositiveIntegerField(default=600)
    daily_budget_usd = models.DecimalField(max_digits=10, decimal_places=4, default="1.0000")


class AIUsageDaily(models.Model):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT)
    date = models.DateField()
    requests = models.PositiveIntegerField(default=0)
    reserved_tokens = models.PositiveIntegerField(default=0)
    consumed_tokens = models.PositiveIntegerField(default=0)
    audio_seconds = models.PositiveIntegerField(default=0)
    reserved_usd = models.DecimalField(max_digits=14, decimal_places=6, default="0.000000")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["tenant", "date"], name="ai_usage_tenant_day")
        ]
