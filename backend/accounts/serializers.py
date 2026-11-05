from rest_framework import serializers

from accounts.models import ClientOrg, User


class ClientOrgSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientOrg
        fields = ["id", "name"]


class UserSerializer(serializers.ModelSerializer):
    client_org = ClientOrgSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "role", "client_org"]
        read_only_fields = fields


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False, write_only=True)
