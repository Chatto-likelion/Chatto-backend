from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    profile_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    credit = models.IntegerField(null=True, default=0)
    phone = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return f"user_id={self.user.id}, point={self.point}"
    
class CreditPurchase(models.Model):
    purchase_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.IntegerField(default=0)
    payment = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

class CreditUsage(models.Model):
    usage_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.IntegerField(default=0)
    usage = models.TextField(default="")
    purpose = models.TextField(default="")
    created_at = models.DateTimeField(auto_now_add=True)