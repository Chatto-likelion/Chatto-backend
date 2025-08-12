from rest_framework.serializers import ModelSerializer
from django.contrib.auth.models import User
from .models import UserProfile, CreditPurchase, CreditUsage
from rest_framework import serializers


class UserIdUsernameSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


class UserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "password", "email"]


class UserProfileSerializer(ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = UserProfile
        fields = "__all__"

class CreditPurchaseSerializer(ModelSerializer):
    class Meta:
        model = CreditPurchase
        fields = "__all__"

class CreditUsageSerializer(ModelSerializer):
    class Meta:
        model = CreditUsage
        fields = "__all__"