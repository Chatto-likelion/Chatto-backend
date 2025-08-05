from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.
class ChatPlay(models.Model):
    chat_id = models.AutoField(primary_key=True)
    title = models.TextField()
    file = models.FileField(upload_to='chat_files_play/')
    people_num = models.IntegerField()
    uploaded_at = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

class ResultPlayChem(models.Model):
    result_id = models.AutoField(primary_key=True)
    content = models.TextField()
    is_saved = models.BooleanField(default=False)
    relationship = models.TextField(default="")
    situation = models.TextField(default="")
    analysis_date_start = models.TextField(default="")
    analysis_date_end = models.TextField(default="")
    analysis_date = models.DateTimeField(default=timezone.now)
    chat = models.ForeignKey(ChatPlay, on_delete=models.CASCADE)

class ResultPlaySome(models.Model):
    result_id = models.AutoField(primary_key=True)
    content = models.TextField()
    is_saved = models.BooleanField(default=False)
    relationship = models.TextField(default="")
    age = models.TextField(default="")
    analysis_date_start = models.TextField(default="")
    analysis_date_end = models.TextField(default="")
    analysis_date = models.DateTimeField(default=timezone.now)
    chat = models.ForeignKey(ChatPlay, on_delete=models.CASCADE)

class ResultPlayMBTI(models.Model):
    result_id = models.AutoField(primary_key=True)
    content = models.TextField()
    is_saved = models.BooleanField(default=False)
    analysis_date_start = models.TextField(default="")
    analysis_date_end = models.TextField(default="")
    analysis_date = models.DateTimeField(default=timezone.now)
    chat = models.ForeignKey(ChatPlay, on_delete=models.CASCADE)
