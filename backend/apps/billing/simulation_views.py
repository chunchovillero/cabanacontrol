from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.profile import StrictInput
from apps.accounts.throttling import consume_limit
from apps.billing.models import CheckoutAttempt, PlanPrice, SimulatedContract, SimulationCompany
from apps.billing.simulation import TERMS, accept_quote, manage_intent, quote, simulate_result
from apps.tenants.permissions import HasConsistentTenant, IsTenantOwner


class PriceSerializer(serializers.Serializer):
    code = serializers.CharField(source="plan.code")
    name = serializers.CharField(source="plan.name")
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    currency = serializers.CharField()
    version = serializers.IntegerField()


class AttemptSerializer(serializers.ModelSerializer):
    code = serializers.CharField(source="price.plan.code")
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        model = CheckoutAttempt
        fields = [
            "id",
            "kind",
            "code",
            "amount",
            "state",
            "quoted_at",
            "expires_at",
            "contract_revision",
        ]


class ContractSerializer(serializers.ModelSerializer):
    code = serializers.CharField(source="price.plan.code")
    next_code = serializers.SerializerMethodField()

    def get_next_code(self, obj) -> str | None:
        return obj.next_price.plan.code if obj.next_price_id else None

    class Meta:
        model = SimulatedContract
        fields = [
            "code",
            "next_code",
            "revision",
            "period_start",
            "period_end",
            "cancel_at_end",
            "finalized",
        ]


class StateSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    terms_version = serializers.CharField()
    prices = PriceSerializer(many=True)
    contract = ContractSerializer(allow_null=True)
    attempts = AttemptSerializer(many=True)


class QuoteInput(StrictInput):
    code = serializers.ChoiceField(choices=["initial", "growth", "operator"])
    expected_revision = serializers.IntegerField(min_value=0)


class AcceptInput(StrictInput):
    key = serializers.UUIDField()
    terms = serializers.CharField(max_length=30)
    consent = serializers.BooleanField()

    def validate_consent(self, value):
        if not value:
            raise serializers.ValidationError(
                "Acepta importe, condiciones y renovación expresamente."
            )
        return value


class ResultInput(StrictInput):
    event_id = serializers.UUIDField()
    result = serializers.ChoiceField(choices=["approved", "rejected", "pending", "uncertain"])


class IntentInput(StrictInput):
    operation = serializers.ChoiceField(choices=["cancel", "resume", "downgrade", "clear_change"])
    expected_revision = serializers.IntegerField(min_value=1)
    code = serializers.ChoiceField(choices=["initial", "growth", "operator"], required=False)
    terms = serializers.CharField(max_length=30, required=False)
    consent = serializers.BooleanField(required=False, default=False)

    def validate(self, data):
        data = super().validate(data)
        if data["operation"] in ("resume", "downgrade") and (
            not data["consent"] or not data.get("terms")
        ):
            raise serializers.ValidationError("Revisa precio y acepta renovación y condiciones.")
        if data["operation"] in ("resume", "downgrade") and not data.get("code"):
            raise serializers.ValidationError("Selecciona el plan.")
        data.pop("consent")
        return data


class OwnerSimulationView(APIView):
    permission_classes = [HasConsistentTenant, IsTenantOwner]


class SimulationStateView(OwnerSimulationView):
    @extend_schema(responses=StateSerializer)
    def get(self, request):
        enabled = (
            settings.DEBUG
            and settings.BILLING_SIMULATION_ENABLED
            and SimulationCompany.objects.filter(tenant=request.tenant).exists()
        )
        contract = None
        attempts = []
        prices = []
        if enabled:
            contract = (
                SimulatedContract.objects.select_related("price__plan", "next_price__plan")
                .filter(tenant=request.tenant)
                .first()
            )
            prices = PlanPrice.objects.select_related("plan").order_by("amount")
            attempts = (
                CheckoutAttempt.objects.filter(tenant=request.tenant)
                .select_related("price__plan")
                .order_by("-quoted_at")[:20]
            )
        return Response(
            StateSerializer(
                {
                    "enabled": enabled,
                    "terms_version": TERMS,
                    "prices": prices,
                    "contract": contract,
                    "attempts": attempts,
                }
            ).data
        )


class QuoteView(OwnerSimulationView):
    @extend_schema(request=QuoteInput, responses={201: AttemptSerializer})
    def post(self, request):
        data = QuoteInput(data=request.data)
        data.is_valid(raise_exception=True)
        consume_limit("billing-quotes:user", str(request.user.pk), 60, window_seconds=3600)
        return Response(
            AttemptSerializer(
                quote(actor=request.user, tenant=request.tenant, **data.validated_data)
            ).data,
            status=201,
        )


class AcceptView(OwnerSimulationView):
    @extend_schema(request=AcceptInput, responses=AttemptSerializer)
    def post(self, request, attempt_id):
        data = AcceptInput(data=request.data)
        data.is_valid(raise_exception=True)
        values = dict(data.validated_data)
        values.pop("consent")
        return Response(
            AttemptSerializer(
                accept_quote(
                    actor=request.user, tenant=request.tenant, attempt_id=attempt_id, **values
                )
            ).data
        )


class ResultView(OwnerSimulationView):
    @extend_schema(request=ResultInput, responses=AttemptSerializer)
    def post(self, request, attempt_id):
        data = ResultInput(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(
            AttemptSerializer(
                simulate_result(
                    actor=request.user,
                    tenant=request.tenant,
                    attempt_id=attempt_id,
                    **data.validated_data,
                )
            ).data
        )


class IntentView(OwnerSimulationView):
    @extend_schema(request=IntentInput, responses=ContractSerializer)
    def post(self, request):
        data = IntentInput(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(
            ContractSerializer(
                manage_intent(actor=request.user, tenant=request.tenant, **data.validated_data)
            ).data
        )
