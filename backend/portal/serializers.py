from rest_framework import serializers

from portal.models import ClientDecision, InterviewSlot


class DecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=ClientDecision.Decision.choices)
    reason = serializers.CharField(max_length=500, allow_blank=True, required=False, default="")

    def validate(self, attrs):
        if attrs["decision"] == ClientDecision.Decision.REJECT and not attrs["reason"].strip():
            raise serializers.ValidationError({"reason": "A reason is required to reject a candidate."})
        return attrs


class SlotSerializer(serializers.Serializer):
    starts_at = serializers.DateTimeField()
    duration_minutes = serializers.IntegerField(min_value=15, max_value=240, default=30)
    note = serializers.CharField(max_length=300, allow_blank=True, required=False, default="")


class SlotResponseSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[InterviewSlot.Status.CONFIRMED, InterviewSlot.Status.DECLINED])
