from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class UserProfile(models.Model):
    profile_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    point = models.IntegerField()
    phone = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return f"user_id={self.user.id}, point={self.point}"
