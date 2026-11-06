from rest_framework import serializers

from candidates.models import Stage


class SubmitSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=500, allow_blank=True, required=False, default="")


class StageMoveSerializer(serializers.Serializer):
    stage = serializers.ChoiceField(choices=Stage.choices)
    reason = serializers.CharField(max_length=500, allow_blank=True, required=False, default="")


class DeletionSerializer(serializers.Serializer):
    requester = serializers.CharField(max_length=120, default="candidate")
    confirm = serializers.BooleanField()

    def validate_confirm(self, value):
        if not value:
            raise serializers.ValidationError("Confirm the deletion request.")
        return value
