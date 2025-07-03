from rest_framework import serializers

class ChatUploadRequestSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    file = serializers.FileField()

class ChatAnalysisRequestSerializer(serializers.Serializer):
    people_num = serializers.IntegerField()
    rel = serializers.CharField(max_length=255) 
    situation = serializers.CharField(max_length=255)
    analysis_start = serializers.DateTimeField()
    analysis_end = serializers.DateTimeField()
