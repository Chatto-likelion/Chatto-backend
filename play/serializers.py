from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import(
    ChatPlay, 
    ResultPlayChem,
    ResultPlaySome,
    ResultPlayMBTI,
    ResultPlaySomeSpec,
    ResultPlayMBTISpec,
    ResultPlayMBTISpecPersonal
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

###################################################################

class SomeSpecSerializerPlay(ModelSerializer):
    class Meta:
        model = ResultPlaySomeSpec
        fields = "__all__"

class MBTISpecSerializerPlay(ModelSerializer):
    class Meta:
        model = ResultPlayMBTISpec
        fields = "__all__"

class MBTISpecPersonalSerializerPlay(ModelSerializer):
    class Meta:
        model = ResultPlayMBTISpecPersonal
        fields = "__all__"

###################################################################

class SomeAllSerializerPlay(serializers.Serializer):
    result = SomeResultSerializerPlay()
    spec = SomeSpecSerializerPlay()

class MBTIAllSerializerPlay(serializers.Serializer):
    result = MBTIResultSerializerPlay()
    spec = MBTISpecSerializerPlay()
    spec_personal = MBTISpecPersonalSerializerPlay()
