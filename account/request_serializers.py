from rest_framework import serializers


class SignUpRequestSerializer(serializers.Serializer):
    username = serializers.CharField()
    phone = serializers.CharField()
    email = serializers.CharField()
    verf_num = serializers.CharField()
    password = serializers.CharField()
    password_confirm = serializers.CharField()


class SignInRequestSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class ProfileEditRequestSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.CharField()
    phone = serializers.CharField()
    password = serializers.CharField()

class TokenRefreshRequestSerializer(serializers.Serializer):
    refresh = serializers.CharField()
    
