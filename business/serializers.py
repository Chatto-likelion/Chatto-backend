from rest_framework.serializers import ModelSerializer
from django.contrib.auth.models import User
from rest_framework import serializers

class UploadResponseSerializer(serializers.Serializer):
    chat_id_bus_contrib = serializers.IntegerField()

class ListResponseSerializer(serializers.Serializer):
    chat_id_bus_contrib = serializers.IntegerField()
    title = serializers.CharField(max_length=255)
    people_num = serializers.IntegerField()
    updated_at = serializers.DateTimeField()

class AnalyseResponseSerializer(serializers.Serializer):
    result_id_bus_contrib = serializers.IntegerField()