from rest_framework import serializers


class SignUpRequestSerializer(serializers.Serializer):
    username = serializers.CharField()
    phone = serializers.IntegerField()
    email = serializers.CharField()
    verf_num = serializers.CharField()
    password = serializers.CharField()
    password_confirm = serializers.CharField()


class SignInRequestSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()



    
