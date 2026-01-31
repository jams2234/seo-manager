from django.db import models
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
import os


class 가위바위보_타이머(models.Model):
    id = models.AutoField(primary_key=True)
    매칭대기시간 = models.IntegerField(blank=False, null=False)
    가위바위보_선택시간 = models.IntegerField(blank=False, null=False)
    
    def __str__(self):
        return str(self.id)
    class Meta: 
        verbose_name_plural = "가위바위보 타이머"
        ordering = ['-id']



class 가위바위보(models.Model):
    id = models.AutoField(primary_key=True)
    텔레그램ID = models.CharField(max_length=50, blank=False, null=False)
    이름 = models.CharField(max_length=50, blank=False, null=False)
    TRX입력 = models.BooleanField(blank=False, null=False, default=False)
    TRX = models.IntegerField(blank=True, null=True)
    선택 = models.CharField(max_length=10, blank=False, null=False, default='None')
    생성일 = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return str(self.id)
    class Meta: 
        verbose_name_plural = "가위바위보 실시간"
        ordering = ['-id']



class 계급(models.Model):
    id = models.AutoField(primary_key=True)
    계급 = models.CharField(max_length=50, blank=False, null=False)
    채팅 = models.IntegerField(blank=False, null=False)
    보상률 = models.FloatField(blank=False, null=False)
    
    def __str__(self):
        return str(self.계급)
    class Meta: 
        verbose_name_plural = "계급"
        ordering = ['-id']


class 유저(models.Model):
    id = models.AutoField(primary_key=True)
    텔레그램ID = models.CharField(max_length=50, blank=False, null=False)
    이름 = models.CharField(max_length=50, blank=False, null=False)
    계급 = models.ForeignKey(계급, on_delete=models.DO_NOTHING)
    이번주_채팅 = models.IntegerField(blank=False, null=False, default=0)
    채팅 = models.IntegerField(blank=False, null=False, default=0)
    오늘출석 = models.BooleanField(blank=False, null=False, default=False)
    TRX = models.FloatField(blank=False, null=False, default=0)
    reward_threshold = models.IntegerField(blank=False, null=False, default=3)
    
    # 트레이딩게임 관련 필드 (버전: 1.0.0, 날짜: 2025-12-30)
    트레이딩게임_누적_승리 = models.IntegerField(blank=False, null=False, default=0)
    트레이딩게임_누적_패배 = models.IntegerField(blank=False, null=False, default=0)
    트레이딩게임_연승 = models.IntegerField(blank=False, null=False, default=0)
    트레이딩게임_총수익 = models.IntegerField(blank=False, null=False, default=0)

    def __str__(self):
        return str(self.텔레그램ID)
    class Meta: 
        verbose_name_plural = "유저"
        ordering = ['-id']


# 트레이딩게임 관련 모델 (버전: 1.0.0, 날짜: 2025-12-30)
CANDLE_CHOICES = (
    ('5분',  '5분'),
    ('15분', '15분'),
    ('30분', '30분'),
    ('1시간','1시간'),
)


class 트레이딩게임(models.Model):
    id = models.AutoField(primary_key=True)
    캔들 = models.CharField(choices=CANDLE_CHOICES, blank=False, null=False, max_length=10)
    시가 = models.FloatField(blank=False, null=False)
    종가 = models.FloatField(blank=True, null=True)
    방향 = models.CharField(max_length=10, blank=True, null=True)
    베팅중 = models.BooleanField(blank=False, null=False, default=True)
    진행중 = models.BooleanField(blank=False, null=False, default=True)
    생성일 = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return str(self.id)
    class Meta: 
        verbose_name_plural = "트레이딩게임 실시간"
        ordering = ['-id']
        

        
class 트레이딩게임_베팅(models.Model):
    id = models.AutoField(primary_key=True)
    게임ID = models.IntegerField(blank=False, null=False)
    텔레그램ID = models.CharField(max_length=50, blank=False, null=False)
    방향 = models.CharField(max_length=10, blank=False, null=False, default='미입력')
    TRX = models.IntegerField(blank=False, null=False, default=0)
    생성일 = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return str(self.id)
    class Meta: 
        verbose_name_plural = "트레이딩게임 기록"
        ordering = ['-id']


        
class 트레이딩게임_설정(models.Model):
    id = models.AutoField(primary_key=True)
    캔들 = models.CharField(choices=CANDLE_CHOICES, blank=False, null=False, max_length=10)
    베팅마감시간 = models.IntegerField(blank=False, null=False)
    이미지 = models.FileField(upload_to='static/', blank=True, null=True)
    
    def __str__(self):
        return str(self.id)
    class Meta: 
        verbose_name_plural = "트레이딩게임 설정"
        ordering = ['-id']
        
        

@receiver(post_delete, sender=트레이딩게임_설정)
def post_delete_image(sender, instance, *args, **kwargs):
    try:
        instance.이미지.delete(save=False)
    except:
        pass
    
@receiver(pre_save, sender=트레이딩게임_설정)
def pre_save_image(sender, instance, *args, **kwargs):
    try:
        old_img = instance.__class__.objects.get(id=instance.id).이미지.path
        try:
            new_img = instance.이미지.path
        except:
            new_img = None
        if new_img != old_img:
            if os.path.exists(old_img):
                os.remove(old_img)
    except:
        pass