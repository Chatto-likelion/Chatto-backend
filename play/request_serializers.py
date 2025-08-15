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

class ChemQuizSolveDetailRequestSerializerPlay(serializers.Serializer):
    name = serializers.CharField()
    answer = serializers.IntegerField()

class ChemQuizStartRequestSerializerPlay(serializers.Serializer):
    name = serializers.CharField()
    
class ChemQuizSubmissionRequestSerializerPlay(serializers.Serializer):
    name = serializers.CharField()

class ChemQuizPersonalViewRequestSerializerPlay(serializers.Serializer):
    name = serializers.CharField()

class ChemQuizResultViewRequestSerializerPlay(serializers.Serializer):
    name = serializers.CharField()

class ChemQuizModifyRequestSerializerPlay(serializers.Serializer):
    question = serializers.CharField()
    choice1 = serializers.CharField()
    choice2 = serializers.CharField()
    choice3 = serializers.CharField()
    choice4 = serializers.CharField()
    answer = serializers.IntegerField()

class ChemQuizSubmitRequestSerializerPlay(serializers.Serializer):
    answer = serializers.IntegerField()

class ChatTitleModifyRequestSerializerPlay(serializers.Serializer):
    title = serializers.CharField()