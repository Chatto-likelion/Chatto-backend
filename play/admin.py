from django.contrib import admin
from play.models import (
    ChatPlay,
    ResultPlayChem,
    ResultPlaySome,
    ResultPlayMBTI,
    ResultPlayChemSpec,
    ResultPlayChemSpecTable,
    ResultPlaySomeSpec,
    ResultPlayMBTISpec,
    ResultPlayMBTISpecPersonal,
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
)

# Register your models here.

admin.site.register(ChatPlay)
admin.site.register(ResultPlayChem)
admin.site.register(ResultPlaySome)
admin.site.register(ResultPlayMBTI)
admin.site.register(ResultPlayChemSpec)
admin.site.register(ResultPlayChemSpecTable)
admin.site.register(ResultPlaySomeSpec)
admin.site.register(ResultPlayMBTISpec)
admin.site.register(ResultPlayMBTISpecPersonal)
admin.site.register(ChemQuiz)
admin.site.register(ChemQuizQuestion)
admin.site.register(ChemQuizPersonal)
admin.site.register(ChemQuizPersonalDetail)
admin.site.register(SomeQuiz)
admin.site.register(SomeQuizQuestion)
admin.site.register(SomeQuizPersonal)
admin.site.register(SomeQuizPersonalDetail)
admin.site.register(MBTIQuiz)
admin.site.register(MBTIQuizQuestion)
admin.site.register(MBTIQuizPersonal)
admin.site.register(MBTIQuizPersonalDetail)
