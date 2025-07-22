from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import ChatBus, ResultBusContrib

class AnalyseResponseSerializerBus(serializers.Serializer):
    result_id_ = serializers.IntegerField()

class ChatSerializerBus(ModelSerializer):
    class Meta:
        model = ChatBus
        fields = "__all__"

class ResultSerializerBus(ModelSerializer):
    class Meta:
        model = ResultBusContrib
        fields = "__all__"