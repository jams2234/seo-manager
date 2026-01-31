#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import signal
import sys
import os

# Django 프로젝트 경로 설정
sys.path.insert(0, '/root/telegram_bot')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'telegram_bot.settings')

import django
django.setup()

from telegram import Update, ChatMember, Chat, MessageEntity, ChatPermissions
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext
from CoinGryComm.models import 유저, 계급


# --- 봇 토큰과 그룹 ID ---
BOT_TOKEN = "7286649185:AAH0q7qGhiS1jSLwYLV_u-fj65nnSakBmY0"  # 광고차단 전용 토큰
ALLOWED_GROUP_IDS = [-1001274260156, -1002238611747]

# 로깅 설정 (WARNING 레벨 이상만 표시)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING
)
logger = logging.getLogger(__name__)

def ignore_sigint(signum, frame):
    """
    Ctrl+C(SIGINT) 시그널을 무시하는 핸들러
    """
    pass

# SIGINT 시그널을 무시하도록 설정
signal.signal(signal.SIGINT, ignore_sigint)


def is_user_admin(update: Update, context: CallbackContext) -> bool:
    """
    해당 메시지 유저가 그룹의 관리자인지 확인
    """
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    chat_member = context.bot.get_chat_member(chat_id, user_id)
    return chat_member.status in [ChatMember.ADMINISTRATOR, ChatMember.CREATOR]


def is_rank_allowed_for_links(telegram_id: int) -> bool:
    """
    유저 계급이 '일병' 이상인지 확인
    - 일병 이상: 링크 허용 (True)
    - 훈련병: 링크 차단 (False)
    - DB 조회 실패: 차단 (False)
    """
    try:
        user = 유저.objects.select_related('계급').get(텔레그램ID=str(telegram_id))
        
        # 일병의 채팅 요구사항 조회
        try:
            일병 = 계급.objects.get(계급='일병')
            # 유저 계급의 채팅 요구사항이 일병 이상이면 허용
            is_allowed = user.계급.채팅 >= 일병.채팅
            
            if is_allowed:
                logger.info(f"[링크 허용] 텔레그램ID={telegram_id}, 계급={user.계급.계급}")
            else:
                logger.info(f"[링크 차단] 텔레그램ID={telegram_id}, 계급={user.계급.계급} (일병 미만)")
            
            return is_allowed
            
        except 계급.DoesNotExist:
            logger.warning(f"[계급 조회 실패] '일병' 계급이 DB에 없음")
            return False
            
    except 유저.DoesNotExist:
        logger.warning(f"[유저 조회 실패] 텔레그램ID={telegram_id} - DB에 미등록")
        return False
        
    except Exception as e:
        logger.error(f"[계급 조회 오류] 텔레그램ID={telegram_id}, 오류={e}")
        return False

def message_handler(update: Update, context: CallbackContext):
    """
    메시지를 수신할 때마다 실행되는 핸들러 함수
    """
    chat = update.effective_chat
    user = update.effective_user

    # ① 허용된 그룹ID가 아니면 무시
    if chat.id not in ALLOWED_GROUP_IDS:
        return

    # ② 그룹/슈퍼그룹만 처리
    if chat.type not in [Chat.GROUP, Chat.SUPERGROUP]:
        return

    # 봇(자신)이 보낸 메시지는 무시
    if user.is_bot:
        return
    
    # 관리자라면 무시
    if is_user_admin(update, context):
        return
    
    # ★ 일병 이상 계급이면 링크 허용
    if is_rank_allowed_for_links(user.id):
        return
    
    message = update.message
    # 메시지 엔티티(하이퍼링크 등) 확인
    if message and message.entities:
        for entity in message.entities:
            if entity.type in [MessageEntity.URL, MessageEntity.TEXT_LINK]:
                kick_user_and_notify(update, context)
                return
    
    # 단순 문자열 링크(옵션)도 검사
    text = message.text if message.text else ""
    if any(link_keyword in text.lower() for link_keyword in ["http", "https", "www"]):
        kick_user_and_notify(update, context)


def kick_user_and_notify(update: Update, context: CallbackContext):
    """
    필터된 메시지를 삭제하고, 사용자 메시지 전송 권한을 제한한 뒤 안내 메시지를 보내는 함수
    """
    chat = update.effective_chat
    user = update.effective_user
    
    # 1) 검열된 메시지 삭제 (bot이 "메시지 삭제" 권한이 있어야 함)
    try:
        update.message.delete()
    except Exception as e:
        logger.warning(f"메시지 삭제 실패: {e}")
    
    # 2) 메시지 전송 권한 제한
    try:
        context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=user.id,
            permissions=ChatPermissions(
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False
            )
        )
    except Exception as e:
        logger.warning(f"권한 제한 실패: {e}")

    # 3) 안내 메시지
    context.bot.send_message(
        chat_id=chat.id,
        text=(
            f'🚫 링크 차단: "{user.full_name}"님\n'
            f'💡 일병 이상 계급부터 링크 전송 가능\n'
            f'📝 출석+채팅으로 승급하세요!'
        )
    )


def main():
    # Updater/Dispatcher 초기화
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # 메시지 핸들러 등록
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handler))

    logger.warning("광고차단 봇 시작 (광고차단 전용 토큰, 일병 이상 링크 허용)")
    
    # 봇 실행
    updater.start_polling()
    # 프로그램을 계속 실행 (Ctrl+C를 눌러도 종료되지 않음)
    updater.idle()

if __name__ == "__main__":
    main()
