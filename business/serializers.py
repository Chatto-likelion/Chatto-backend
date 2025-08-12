from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import (
    ChatBus, 
    ResultBusContrib,
    ResultBusContribSpec,
    ResultBusContribSpecPersonal,
    ResultBusContribSpecPeriod,
)

class AnalyseResponseSerializerBus(serializers.Serializer):
    result_id_ = serializers.IntegerField()

class ChatSerializerBus(ModelSerializer):
    class Meta:
        model = ChatBus
        fields = "__all__"

class ContribResultSerializerBus(ModelSerializer):
    class Meta:
        model = ResultBusContrib
        fields = "__all__"

class ContribSpecSerializerBus(ModelSerializer):
    class Meta:
        model = ResultBusContribSpec
        fields = "__all__"

class ContribSpecPersonalSerializerBus(ModelSerializer):
    class Meta:
        model = ResultBusContribSpecPersonal
        fields = "__all__"

class ContribSpecPeriodSerializerBus(ModelSerializer):
    class Meta:
        model = ResultBusContribSpecPeriod
        fields = "__all__"

class ContribAllSerializerBus(serializers.Serializer):
    result = ContribResultSerializerBus()
    spec = ContribSpecSerializerBus()
    spec_personal = ContribSpecPersonalSerializerBus(many=True)
    spec_period = ContribSpecPeriodSerializerBus(many=True)