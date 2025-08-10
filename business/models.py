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
    title = models.TextField(default = "")
    people_num = models.IntegerField(default=0)
    is_saved = models.BooleanField(default=False)
    project_type = models.TextField(default="")
    team_type = models.TextField(default="")
    analysis_date_start = models.TextField(default="")
    analysis_date_end = models.TextField(default="")
    created_at = models.DateTimeField(default=timezone.now)
    chat = models.ForeignKey(ChatBus, on_delete=models.SET_NULL, null=True, blank=True)