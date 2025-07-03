from django.db import models
from django.utils import timezone

# Create your models here.
class ChatsPlayChem(models.Model):
    chat_id_play_chem = models.AutoField(primary_key=True, verbose_name="채팅번호")
    title = models.CharField(max_length=255, verbose_name="제목")
    file = models.FileField(upload_to='uploads/', verbose_name="파일")
    people_num = models.IntegerField(verbose_name="사람 수")
    uploaded_at = models.DateTimeField(default=timezone.now, verbose_name="업로드 시간")
    user_id = models.IntegerField(verbose_name="유저번호")

    def __str__(self):
        return f"{self.chat_id_play_chem}"

class ResultPlayChem(models.Model):
    result_id_play_chem = models.AutoField(primary_key=True, verbose_name="결과번호")
    content = models.TextField(verbose_name="분석내용")
    is_saved = models.IntegerField(verbose_name="저장여부")
    analysis_date = models.DateTimeField(verbose_name="분석날짜", default=timezone.now)
    analysis_type = models.CharField(max_length=100, verbose_name="분석종류")
    chat_id_play_chem = models.IntegerField(verbose_name="채팅번호")

    def __str__(self):
        return f"{self.result_id_play_chem}"