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
    content = models.TextField()
    is_saved = models.BooleanField(default=False)
    analysis_date = models.DateTimeField(default=timezone.now)
    analysis_type = models.TextField()
    chat = models.ForeignKey(ChatBus, on_delete=models.CASCADE)