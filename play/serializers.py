from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import ChatPlay, ResultPlayChem

class AnalyseResponseSerializerPlay(serializers.Serializer):
    result_id_ = serializers.IntegerField()


class ChatSerializerPlay(ModelSerializer):
    class Meta:
        model = ChatPlay
        fields = "__all__"

class ResultSerializerPlay(ModelSerializer):
    class Meta:
        model = ResultPlayChem
        fields = "__all__"