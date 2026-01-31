"""
트레이딩게임 Admin 설정 모듈
버전: 1.0.0
날짜: 2025-12-30
설명: 트레이딩게임 관련 Django Admin 설정
"""
from django.contrib import admin
from CoinGryComm.models import *


@admin.register(가위바위보_타이머)
class 가위바위보_타이머Admin(admin.ModelAdmin):
    list_display = ['매칭대기시간','가위바위보_선택시간']
    list_display_links = ['매칭대기시간','가위바위보_선택시간']
    list_per_page = 100


@admin.register(가위바위보)
class 가위바위보Admin(admin.ModelAdmin):
    list_display = ['텔레그램ID','이름','TRX입력','TRX','선택','생성일']
    list_display_links = ['텔레그램ID','이름','TRX입력','TRX','선택','생성일']
    list_per_page = 100


@admin.register(계급)
class 계급Admin(admin.ModelAdmin):
    list_display = ['계급','채팅','보상률']
    list_display_links = ['계급','채팅','보상률']
    list_per_page = 100

@admin.register(유저)
class 유저Admin(admin.ModelAdmin):
    list_display = ['텔레그램ID','이름','계급','이번주_채팅','채팅','오늘출석','TRX','reward_threshold','트레이딩게임_누적_승리']
    list_display_links = ['텔레그램ID','이름','계급','이번주_채팅','채팅','오늘출석','TRX','reward_threshold','트레이딩게임_누적_승리']
    search_fields = ['텔레그램ID','이름']
    list_filter = ['오늘출석','계급']
    list_per_page = 100
    
    
@admin.register(트레이딩게임)
class 트레이딩게임Admin(admin.ModelAdmin):
    list_display = ['id','캔들','시가','종가','방향','베팅중','진행중','생성일']
    list_display_links = ['id','캔들','시가','종가','방향','베팅중','진행중','생성일']
    search_fields = ['id','방향']
    list_per_page = 100
    
    
@admin.register(트레이딩게임_베팅)
class 트레이딩게임_베팅Admin(admin.ModelAdmin):
    list_display = ['게임ID','텔레그램ID','방향','TRX','생성일']
    list_display_links = ['게임ID','텔레그램ID','방향','TRX','생성일']
    search_fields = ['텔레그램ID','게임ID','방향']
    list_per_page = 100
    
    
@admin.register(트레이딩게임_설정)
class 트레이딩게임_설정Admin(admin.ModelAdmin):
    list_display = ['캔들','베팅마감시간','이미지']
    list_display_links = ['캔들','베팅마감시간','이미지']
    list_per_page = 100