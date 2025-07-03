from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.
class Chat(models.Model):
    chat_id_bus_contrib = models.AutoField(primary_key=True)
    title = models.TextField()
    content = models.FileField(upload_to='chat_files/')
    people_num = models.IntegerField()
    updated_at = models.DateTimeField(auto_now=True)
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"chat_id_bus_contrib={self.chat_id_bus_contrib}, title={self.title}, user_id={self.user_id}"
    
class ResultBusContrib(models.Model):
    result_id_bus_contrib = models.AutoField(primary_key=True)
    content = models.TextField()
    is_saved = models.BooleanField(default=False)
    analysis_date = models.DateField(default=timezone.now)
    analysis_type = models.TextField()
    chat_id_bus_contrib = models.ForeignKey(Chat, on_delete=models.CASCADE)

    def __str__(self):
        return f"result_id_bus_contrib={self.result_id_bus_contrib}, content={self.content[:50]}, chat_id_bus_contrib={self.chat_id_bus_contrib}"
