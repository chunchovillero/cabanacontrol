import uuid

from django.conf import settings
from django.db import models


class SubscriptionPlan(models.Model):
    code = models.CharField(max_length=20)
    version = models.PositiveIntegerField(default=1)
    name = models.CharField(max_length=80)
    property_limit = models.PositiveIntegerField()
    member_limit = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["code", "version"], name="billing_plan_version_unique"),
            models.CheckConstraint(
                condition=models.Q(property_limit__gt=0, member_limit__gt=0),
                name="billing_positive_capacity",
            ),
        ]


class TenantSubscription(models.Model):
    tenant = models.OneToOneField("tenants.Tenant", on_delete=models.PROTECT, primary_key=True)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    # Explicit activation, separate from assignment and schema migration.
    enforced = models.BooleanField(default=False)
    trial_started_at = models.DateTimeField(null=True, blank=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    trial_used = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(trial_started_at__isnull=True, trial_ends_at__isnull=True)
                    | models.Q(
                        trial_started_at__isnull=False,
                        trial_ends_at__isnull=False,
                        trial_ends_at__gt=models.F("trial_started_at"),
                        trial_used=True,
                    )
                ),
                name="billing_trial_dates_valid",
            )
        ]


class SubscriptionEvent(models.Model):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=30)
    reason = models.CharField(max_length=300)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)


class SimulationCompany(models.Model):
    tenant = models.OneToOneField("tenants.Tenant", on_delete=models.PROTECT, primary_key=True)
    enabled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)


class PlanPrice(models.Model):
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT)
    version = models.PositiveIntegerField(default=1)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="CLP")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["plan", "version"], name="billing_price_version_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gt=0, currency="CLP"), name="billing_price_positive_clp"
            ),
        ]


class SimulatedContract(models.Model):
    tenant = models.OneToOneField("tenants.Tenant", on_delete=models.PROTECT, primary_key=True)
    price = models.ForeignKey(PlanPrice, on_delete=models.PROTECT, related_name="contracts")
    next_price = models.ForeignKey(
        PlanPrice, on_delete=models.PROTECT, null=True, related_name="scheduled_contracts"
    )
    revision = models.PositiveIntegerField(default=1)
    anchor = models.DateTimeField()
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    period_index = models.PositiveIntegerField(default=1)
    cancel_at_end = models.BooleanField(default=False)
    finalized = models.BooleanField(default=False)
    consent_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    consent_at = models.DateTimeField()
    terms_version = models.CharField(max_length=30)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(period_end__gt=models.F("period_start")),
                name="billing_contract_period_valid",
            )
        ]


class CheckoutAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT)
    price = models.ForeignKey(PlanPrice, on_delete=models.PROTECT)
    prior_price = models.ForeignKey(
        PlanPrice, on_delete=models.PROTECT, null=True, related_name="upgrades_from"
    )
    kind = models.CharField(
        max_length=10,
        choices=[("purchase", "Compra"), ("upgrade", "Subida"), ("renewal", "Renovación")],
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    contract_revision = models.PositiveIntegerField(default=0)
    retry_number = models.PositiveIntegerField(default=0)
    projection_version = models.DateTimeField()
    quoted_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    state = models.CharField(
        max_length=12,
        default="quoted",
        choices=[
            (x, x)
            for x in [
                "quoted",
                "pending",
                "uncertain",
                "approved",
                "rejected",
                "expired",
                "obsolete",
            ]
        ],
    )
    idempotency_key = models.UUIDField(null=True)
    accepted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True)
    accepted_at = models.DateTimeField(null=True)
    terms_version = models.CharField(max_length=30, blank=True)
    target_start = models.DateTimeField(null=True)
    target_end = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "idempotency_key"],
                condition=models.Q(idempotency_key__isnull=False),
                name="billing_attempt_idempotency",
            ),
            models.UniqueConstraint(
                fields=["tenant"],
                condition=models.Q(state__in=["pending", "uncertain"]),
                name="billing_one_unresolved",
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gte=0), name="billing_attempt_nonnegative"
            ),
        ]


class SimulatedProviderEvent(models.Model):
    id = models.UUIDField(primary_key=True, editable=False)
    attempt = models.ForeignKey(CheckoutAttempt, on_delete=models.PROTECT)
    result = models.CharField(max_length=12)
    outcome = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)


class SaaSCharge(models.Model):
    attempt = models.OneToOneField(CheckoutAttempt, on_delete=models.PROTECT, primary_key=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
