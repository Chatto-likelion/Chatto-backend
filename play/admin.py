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
)
from business.models import (
    ChatBus,
    ResultBusContrib,
    ResultBusContribSpec,
    ResultBusContribSpecPersonal,
    ResultBusContribSpecPeriod,
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

admin.site.register(ChatBus)
admin.site.register(ResultBusContrib)
admin.site.register(ResultBusContribSpec)
admin.site.register(ResultBusContribSpecPersonal)
admin.site.register(ResultBusContribSpecPeriod)