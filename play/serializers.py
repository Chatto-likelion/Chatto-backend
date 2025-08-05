from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import(
    ChatPlay, 
    ResultPlayChem,
    ResultPlaySome,
    ResultPlayMBTI,
) 

class AnalyseResponseSerializerPlay(serializers.Serializer):
    result_id_ = serializers.IntegerField()


class ChatSerializerPlay(ModelSerializer):
    class Meta:
        model = ChatPlay
        fields = "__all__"

class ChemResultSerializerPlay(ModelSerializer):
    class Meta:
        model = ResultPlayChem
        fields = "__all__"

class SomeResultSerializerPlay(ModelSerializer):
    class Meta:
        model = ResultPlaySome
        fields = "__all__"

class MBTIResultSerializerPlay(ModelSerializer):
    class Meta:
        model = ResultPlayMBTI
        fields = "__all__"