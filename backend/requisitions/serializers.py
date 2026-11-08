from rest_framework import serializers

from accounts.models import ClientOrg
from requisitions.models import Requisition


class CriterionInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(max_length=500, allow_blank=True, required=False, default="")
    weight = serializers.IntegerField(min_value=1, max_value=10)
    is_must_have = serializers.BooleanField()


class ScorecardInputSerializer(serializers.Serializer):
    criteria = CriterionInputSerializer(many=True, allow_empty=False, max_length=15)

    def validate_criteria(self, value):
        names = [c["name"].strip().lower() for c in value]
        if len(set(names)) != len(names):
            raise serializers.ValidationError("Criterion names must be unique.")
        return value


class RequisitionCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    client_org = serializers.PrimaryKeyRelatedField(queryset=ClientOrg.objects.all())
    jd_text = serializers.CharField(min_length=20, max_length=20000)


class RequisitionUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Requisition
        fields = ["title", "location", "exp_min_years", "exp_max_years", "notice_max_days", "ctc_min", "ctc_max",
                  "status"]
        extra_kwargs = {f: {"required": False} for f in fields}

    def validate(self, attrs):
        lo = attrs.get("exp_min_years", getattr(self.instance, "exp_min_years", None))
        hi = attrs.get("exp_max_years", getattr(self.instance, "exp_max_years", None))
        if lo is not None and hi is not None and lo > hi:
            raise serializers.ValidationError("Minimum experience cannot exceed maximum.")
        return attrs


class UploadSerializer(serializers.Serializer):
    # empty files are allowed through here so validate_upload can reject just that one with a reason (one bad file never fails the batch)
    files = serializers.ListField(child=serializers.FileField(allow_empty_file=True), allow_empty=False)
    consent_confirmed = serializers.BooleanField()

    def validate_files(self, value):
        from django.conf import settings

        if len(value) > settings.MAX_FILES_PER_BATCH:
            raise serializers.ValidationError(f"At most {settings.MAX_FILES_PER_BATCH} files per batch.")
        return value

    def validate_consent_confirmed(self, value):
        if not value:
            raise serializers.ValidationError("Confirm that candidate consent is on record (hiring use only).")
        return value
