from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.
class ChatBus(models.Model):
    chat_id = models.AutoField(primary_key=True)
    title = models.TextField()
    file = models.FileField(upload_to='chat_files_business/')
    people_num = models.IntegerField()
    uploaded_at = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    
class ResultBusContrib(models.Model):
    result_id = models.AutoField(primary_key=True)
    type = models.IntegerField(default=0)       
    title = models.TextField(default = "")
    people_num = models.IntegerField(default=0)
    is_saved = models.BooleanField(default=False)
    project_type = models.TextField(default="")
    team_type = models.TextField(default="")
    analysis_date_start = models.TextField(default="")
    analysis_date_end = models.TextField(default="")
    created_at = models.DateTimeField(default=timezone.now)
    num_chat = models.IntegerField(default=0)
    chat = models.ForeignKey(ChatBus, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None)

class UuidContrib(models.Model):
    uuid = models.UUIDField(primary_key=True, unique=True)
    result = models.ForeignKey(ResultBusContrib, on_delete=models.CASCADE, null=True, blank=True)

class ResultBusContribSpec(models.Model):
    spec_id = models.AutoField(primary_key=True)
    result = models.ForeignKey(ResultBusContrib, on_delete=models.CASCADE)
    total_talks = models.IntegerField(default=0)
    leader = models.TextField(default="")
    avg_resp = models.IntegerField(default=0)
    insights = models.TextField(default="")
    recommendation = models.TextField(default="")
    analysis_size = models.IntegerField(default=0)

class ResultBusContribSpecPersonal(models.Model):
    specpersonal_id = models.AutoField(primary_key=True)
    spec = models.ForeignKey(ResultBusContribSpec, on_delete=models.CASCADE)
    name = models.TextField(default="")
    rank = models.IntegerField(default=0)
    participation = models.IntegerField(default=0)
    infoshare = models.IntegerField(default=0)
    probsolve = models.IntegerField(default=0)
    proposal = models.IntegerField(default=0)
    resptime = models.IntegerField(default=0)
    analysis = models.TextField(default="")
    type = models.TextField(default="")

class ResultBusContribSpecPeriod(models.Model):
    specperiod_id = models.AutoField(primary_key=True)
    spec = models.ForeignKey(ResultBusContribSpec, on_delete=models.CASCADE)
    name = models.TextField(default="")
    analysis = models.TextField(default="")
    period_1 = models.IntegerField(default=0)
    period_2 = models.IntegerField(default=0)
    period_3 = models.IntegerField(default=0)
    period_4 = models.IntegerField(default=0)
    period_5 = models.IntegerField(default=0)
    period_6 = models.IntegerField(default=0)