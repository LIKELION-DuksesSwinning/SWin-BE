from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    GENDER_CHOICES = (
        ('FEMALE', '여성'),
        ('MALE', '남성'),
    )
    name = models.CharField(max_length=50, null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)
    region = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.username

class UserSkinProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='skin_profile')
    weekly_swim_count = models.IntegerField()
    avg_swim_time = models.IntegerField(help_text="분 단위")
    swim_period = models.CharField(max_length=50)
    skin_type = models.CharField(max_length=20) # 건성, 지성, 복합성, 수부지, 민감성

class UserSkinSymptom(models.Model):
    profile = models.ForeignKey(UserSkinProfile, on_delete=models.CASCADE, related_name='symptoms')
    symptom = models.CharField(max_length=30) # 당김, 건조, 가려움, 붉음, 여드름, 없음

class UserSkinArea(models.Model):
    profile = models.ForeignKey(UserSkinProfile, on_delete=models.CASCADE, related_name='areas')
    area = models.CharField(max_length=30) # 이마, 볼, 나비존, 하관

class Agreement(models.Model):
    TERMS_CHOICES = (
        ('PRIVACY_POLICY', '개인정보 처리방침 및 이용약관'),
        ('THIRD_PARTY_DERNA', '개인정보 제3자 제공 동의서(Derna)'),
        ('THIRD_PARTY_SWIN', '개인정보 제3자 제공 동의서(SWin)'),
        ('SENSITIVE_INFO', '민감정보 수집·이용 동의서'),
        ('MARKETING', '마케팅 정보 수신 동의서'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='agreements')
    terms_type = models.CharField(max_length=30, choices=TERMS_CHOICES)
    is_agreed = models.BooleanField(default=False)
    agreed_at = models.DateTimeField(null=True, blank=True)

class NotificationSetting(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_setting')
    swim_after_record_noti = models.BooleanField(default=True)
    clinic_reservation_noti = models.BooleanField(default=True)
    swim_schedule_noti = models.BooleanField(default=True)
    weekly_report_noti = models.BooleanField(default=True)