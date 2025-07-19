from rest_framework.serializers import ModelSerializer
from django.contrib.auth.models import User
from rest_framework import serializers

class UploadResponseSerializer(serializers.Serializer):
    chat_id = serializers.IntegerField()

class ListResponseSerializer(serializers.Serializer):
    chat_id = serializers.IntegerField()
    title = serializers.CharField(max_length=255)
    people_num = serializers.IntegerField()
    uploaded_at = serializers.DateTimeField()

class AnalyseResponseSerializer(serializers.Serializer):
    result_id_ = serializers.IntegerField()

class AllResultSerializer(serializers.Serializer):
    result_id_bus_contrib = serializers.IntegerField()
    analysis_date = serializers.DateField()
    content = serializers.CharField()
    analysis_type = serializers.CharField(max_length=255)
    analysis_result = serializers.CharField()
    chat_id_bus_contrib = serializers.IntegerField()

class DetailResultSerializer(serializers.Serializer):
    content = serializers.CharField()