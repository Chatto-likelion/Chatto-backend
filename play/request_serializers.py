from rest_framework import serializers

class ChatUploadRequestSerializerPlay(serializers.Serializer):
    file = serializers.FileField()

class ChatChemAnalysisRequestSerializerPlay(serializers.Serializer):
    relationship = serializers.CharField() 
    situation = serializers.CharField()
    analysis_start = serializers.CharField()
    analysis_end = serializers.CharField()

class ChatSomeAnalysisRequestSerializerPlay(serializers.Serializer):
    relationship = serializers.CharField() 
    age = serializers.CharField()
    analysis_start = serializers.CharField()
    analysis_end = serializers.CharField()

class ChatMBTIAnalysisRequestSerializerPlay(serializers.Serializer):
    analysis_start = serializers.CharField()
    analysis_end = serializers.CharField()
