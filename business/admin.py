from django.contrib import admin
from business.models import (
    ChatBus,
    ResultBusContrib,
    ResultBusContribSpec,
    ResultBusContribSpecPersonal,
    ResultBusContribSpecPeriod,
)

admin.site.register(ChatBus)
admin.site.register(ResultBusContrib)
admin.site.register(ResultBusContribSpec)
admin.site.register(ResultBusContribSpecPersonal)
admin.site.register(ResultBusContribSpecPeriod)
