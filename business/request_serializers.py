from rest_framework import serializers

class ChatUploadRequestSerializerBus(serializers.Serializer):
    file = serializers.FileField()

class ChatAnalysisRequestSerializerBus(serializers.Serializer):
    project_type = serializers.CharField() 
    team_type = serializers.CharField()
    analysis_start = serializers.CharField()
    analysis_end = serializers.CharField()

###############################################################

class UuidRequestSerializerBus(serializers.Serializer):
    type = serializers.CharField()