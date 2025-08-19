from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import(
    ChatPlay, 
    ResultPlayChem,
    ResultPlaySome,
    ResultPlayMBTI,
    ResultPlaySomeSpec,
    ResultPlayMBTISpec,
    ResultPlayMBTISpecPersonal,
    ResultPlayChemSpec,
    ResultPlayChemSpecTable,
    ChemQuiz,
    ChemQuizQuestion,
    ChemQuizPersonal,
    ChemQuizPersonalDetail,
    SomeQuiz,
    SomeQuizQuestion,
    SomeQuizPersonal,
    SomeQuizPersonalDetail,
    MBTIQuiz,
    MBTIQuizQuestion,
    MBTIQuizPersonal,
    MBTIQuizPersonalDetail,
    UuidChem,
    UuidMBTI,
    UuidSome,
) 

class AnalyseResponseSerializerPlay(serializers.Serializer):
    result_id_ = serializers.IntegerField()

class QuizCreatedSerializerPlay(serializers.Serializer):
    quiz_id = serializers.IntegerField()

###################################################################

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

class ChemSpecSerializerPlay(ModelSerializer):
    class Meta:
        model = ResultPlayChemSpec
        fields = "__all__"

class ChemSpecTableSerializerPlay(ModelSerializer):
    class Meta:
        model = ResultPlayChemSpecTable
        fields = "__all__"
       
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
    spec_personal = MBTISpecPersonalSerializerPlay(many=True)

class ChemAllSerializerPlay(serializers.Serializer):
    result = ChemResultSerializerPlay()
    spec = ChemSpecSerializerPlay()
    spec_table = ChemSpecTableSerializerPlay(many=True)

###################################################################

class ChemQuizQuestionSerializerPlay(ModelSerializer):
    class Meta:
        model = ChemQuizQuestion
        fields = [
            "quiz_id",
            "question_index",
            "question",
            "choice1",
            "choice2",
            "choice3",
            "choice4",
        ]

class ChemQuizQuestionDetailSerializerPlay(ModelSerializer):
    class Meta:
        model = ChemQuizQuestion
        fields = "__all__"

class ChemQuizInfoSerializerPlay(ModelSerializer):
    class Meta:
        model = ChemQuiz
        fields = "__all__"

class ChemQuizPersonalSerializerPlay(ModelSerializer):
    class Meta:
        model = ChemQuizPersonal
        fields = "__all__"

class ChemQuizPersonalDetailSerializerPlay(ModelSerializer):
    class Meta:
        model = ChemQuizPersonalDetail
        fields = "__all__"

##################################################################

class SomeQuizQuestionSerializerPlay(ModelSerializer):
    class Meta:
        model = SomeQuizQuestion
        fields = [
            "quiz_id",
            "question_index",
            "question",
            "choice1",
            "choice2",
            "choice3",
            "choice4",
        ]

class SomeQuizQuestionDetailSerializerPlay(ModelSerializer):
    class Meta:
        model = SomeQuizQuestion
        fields = "__all__"

class SomeQuizInfoSerializerPlay(ModelSerializer):
    class Meta:
        model = SomeQuiz
        fields = "__all__"

class SomeQuizPersonalSerializerPlay(ModelSerializer):
    class Meta:
        model = SomeQuizPersonal
        fields = "__all__"

class SomeQuizPersonalDetailSerializerPlay(ModelSerializer):
    class Meta:
        model = SomeQuizPersonalDetail
        fields = "__all__"

##################################################################

class MBTIQuizQuestionSerializerPlay(ModelSerializer):
    class Meta:
        model = MBTIQuizQuestion
        fields = [
            "quiz_id",
            "question_index",
            "question",
            "choice1",
            "choice2",
            "choice3",
            "choice4",
        ]

class MBTIQuizQuestionDetailSerializerPlay(ModelSerializer):
    class Meta:
        model = MBTIQuizQuestion
        fields = "__all__"

class MBTIQuizInfoSerializerPlay(ModelSerializer):
    class Meta:
        model = MBTIQuiz
        fields = "__all__"

class MBTIQuizPersonalSerializerPlay(ModelSerializer):
    class Meta:
        model = MBTIQuizPersonal
        fields = "__all__"

class MBTIQuizPersonalDetailSerializerPlay(ModelSerializer):
    class Meta:
        model = MBTIQuizPersonalDetail
        fields = "__all__"

##################################################################

class ChemUuidSerializerPlay(ModelSerializer):
    class Meta:
        model = UuidChem
        fields = "__all__"

class MBTIUuidSerializerPlay(ModelSerializer):
    class Meta:
        model = UuidMBTI
        fields = "__all__"

class SomeUuidSerializerPlay(ModelSerializer):
    class Meta:
        model = UuidSome
        fields = "__all__"
    