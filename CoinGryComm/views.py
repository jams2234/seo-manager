import json, telegram, logging, subprocess, random, time, re
from .models import *
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from 김프봇.김프봇_카카오 import *


logging.basicConfig(
    format='%(asctime)s %(levelname)s [%(filename)s:%(lineno)d]: %(message)s',
    level=logging.ERROR,
    datefmt='%m/%d/%Y %I:%M:%S %p',
    filename="views.log"
)

# ----- [PATCH md2-inline-v1] 메시지 포맷 유틸 -----
MD2_INLINE_PATCH_VERSION = "md2-inline-v1.1"

# Telegram MarkdownV2에서 이모지를 제외하고 단어(또는 줄) 단위로 `...` 감싸기
# - HTML 태그(<b> 등)는 제거
# - 이모지(예: ✌, ✊, ✋, 📈, 📉, ⚠️ 등)는 감싸지 않음
# - 공백/줄바꿈은 그대로 유지
EMOJI_RE = re.compile(r'[\u2600-\u27BF\uFE0F\u200D\U0001F000-\U0001FAFF\U0001F1E6-\U0001F1FF]+', flags=re.UNICODE)

def _strip_html_tags(text: str) -> str:
    # 현재 코드에서 사용하는 <b> 만 제거(필요 시 확장)
    return re.sub(r'</?b>', '', text)

def _wrap_md2_inline(text: str) -> str:
    text = _strip_html_tags(text)

    def wrap_segment(seg: str) -> str:
        # 공백 보존을 위해 split with capture
        tokens = re.split(r'(\s+)', seg)
        out = []
        for tok in tokens:
            if tok.isspace() or tok == '':
                out.append(tok)
                continue
            # tok 안에 이모지와 텍스트가 섞일 수 있으므로, 이모지 경계 기준으로 쪼갠 뒤
            # 이모지는 그대로, 비이모지 부분만 `...` 으로 감싼다.
            parts = EMOJI_RE.split(tok)
            emojis = EMOJI_RE.findall(tok)
            buf = []
            for i, part in enumerate(parts):
                if part:
                    # 백틱 안전 처리
                    safe = part.replace('`', "'")
                    buf.append(f"`{safe}`")
                if i < len(emojis):
                    buf.append(emojis[i])
            out.append(''.join(buf))
        return ''.join(out)

    lines = text.split('\n')
    return '\n'.join(wrap_segment(line) for line in lines)

def send_md2(bot, *, chat_id, text, **kwargs):
    return bot.sendMessage(chat_id=chat_id, text=_wrap_md2_inline(text), parse_mode="MarkdownV2", **kwargs)

def answer_cb_md2(bot, *, callback_query_id, text, show_alert=False):
    # answerCallbackQuery 는 parse_mode 미지원. 팝업 문구에는 백틱을 제외하여 전달.
    # - HTML 태그(<b> 등)는 제거
    # - md2 인라인 감싸기(백틱) 적용하지 않음
    # - 입력 내 역따옴표(`) 문자는 제거
    clean_text = _strip_html_tags(text).replace('`', '')
    return bot.answer_callback_query(callback_query_id=callback_query_id, text=clean_text, show_alert=show_alert)

# ----- [/PATCH md2-inline-v1] -----

def create_rps_buttons():
    keyboard = [
        [InlineKeyboardButton("가위 ✌", callback_data='가위')],
        [InlineKeyboardButton("바위 ✊", callback_data='바위')],
        [InlineKeyboardButton("보 ✋", callback_data='보')]
    ]
    return InlineKeyboardMarkup(keyboard)


@csrf_exempt
def CoinGryComm(request):
    GROUP_IDS = ['-1002238611747']
    출석봇 = '7443544703:AAF-oD55yX68YwrOFk5FR_2szSjDKkoyLPA'
    가위바위보봇 = "7532276504:AAF9YWcOyMSbsIkNhBf5Hhfsf5e9QXk54gA"
    try:
        bot = telegram.Bot(token = 출석봇)
        answer = ((request.body).decode('utf-8'))
        chat_info = json.loads(answer)
        chat_id = chat_info['message']['chat']['id']
        user_id=chat_info['message']['from']['id']
        first_name = chat_info['message']['from']['first_name']
        message_id = chat_info['message']['message_id']

        if str(chat_id) in GROUP_IDS:
            if chat_info['message']['text'] == '/출석체크':
                try:
                    u = 유저.objects.get(텔레그램ID=user_id)
                except:
                    k = 계급.objects.get(계급='훈련병')
                    u = 유저.objects.create(텔레그램ID=user_id, 이름=first_name, 계급=k)
                try: 
                    if first_name != u.이름: u.이름 = first_name
                except: pass
                if u.오늘출석:
                    send_md2(bot, chat_id = chat_id, text = f"{first_name} {u.계급}님, 이미 오늘 출석 체크를 완료하셨습니다.", reply_to_message_id=message_id)
                else:
                    u.오늘출석 = True
                    u.reward_threshold = u.reward_threshold - 1
                    if u.reward_threshold < 1:
                        u.TRX = u.TRX + 1
                        u.reward_threshold = 3
                        send_md2(bot, chat_id = chat_id, text = f"{first_name} {u.계급}님, 출석 포상으로 1 TRX가 지급되었습니다! 다음 포상까지 필요한 출석 체크: {u.reward_threshold}", reply_to_message_id=message_id)
                    else:
                        if u.계급.계급 in ['소위','중위',"대위", "소령", "중령", "대령", "소장", "중장", "장군"]:
                            send_md2(bot, chat_id = chat_id, text = f"{first_name} {u.계급}님 출석 체크 완료! 받들어 총! 충성! 이제부터 채팅 시 계급의 해당하는 일정확률로 TRX를 획득할 수 있습니다. 다음 포상까지 필요한 출석 체크: {u.reward_threshold}", reply_to_message_id=message_id)
                        else:
                            send_md2(bot, chat_id = chat_id, text = f"{first_name} {u.계급}님 출석 체크 완료! 이제부터 채팅 시 계급의 해당하는 일정 확률로 TRX를 획득할 수 있습니다. 다음 포상까지 필요한 출석 체크: {u.reward_threshold}", reply_to_message_id=message_id)
                    u.save()

            
            elif chat_info['message']['text'] == '/vs':
                try:
                    u = 유저.objects.get(텔레그램ID=user_id)
                except:
                    return JsonResponse({"ok": "POST request processed"})
                try:
                    if first_name != u.이름: 
                        u.이름 = first_name
                        u.save()
                except: pass
                bot2 = telegram.Bot(token = 가위바위보봇)
                if len(가위바위보.objects.filter(텔레그램ID=user_id)) > 0:
                    send_md2(bot2, chat_id = chat_id, text = f"{u.이름}님 이미 게임에 참여 중입니다. 게임이 끝난 후 다시 시도하세요.")
                    return JsonResponse({"ok": "POST request processed"})
                if u.TRX < 1:
                    send_md2(bot2, chat_id = chat_id, text = f"{u.이름}님 현재 사용가능한 잔고가 없습니다.")
                    return JsonResponse({"ok": "POST request processed"})
                kbb = 가위바위보.objects.filter(TRX입력 = True)
                if len(kbb) == 0:
                    send_md2(bot2, chat_id = chat_id, text = f"{u.이름}님 게임의 걸 TRX 갯수를 입력해주세요.")
                    가위바위보.objects.create(텔레그램ID=user_id, 이름=u.이름)
                elif len(kbb) == 1:
                    send_md2(bot2, chat_id = chat_id, text = f"{u.이름}님, {kbb[0].이름}님과 가위바위보 매칭을 성사시키려면 동일한 TRX갯수를 보상으로 걸어주세요. 현재 걸린 TRX: {kbb[0].TRX} TRX")
                    가위바위보.objects.create(텔레그램ID=user_id, 이름=u.이름)
                elif len(kbb) > 1:
                    send_md2(bot2, chat_id = chat_id, text = f"{u.이름}님 현재 게임이 진행중입니다. 게임이 끝난 후 다시 시도하세요.")

                
            elif chat_info['message']['text'] == '/행정반':
                try:
                    u = 유저.objects.get(텔레그램ID=user_id)
                except:
                    send_md2(bot, chat_id = chat_id, text = f"사용자 정보를 찾을 수 없습니다.", reply_to_message_id=message_id)
                    return JsonResponse({"ok": "POST request processed"})
                try:
                    if first_name != u.이름: 
                        u.이름 = first_name
                        u.save()
                except: pass
                send_md2(bot, chat_id = chat_id, text = f"유저 : {first_name}\n계급: {u.계급}\n전체 채팅 횟수: {u.채팅}\n보유 TRX: {u.TRX}\n다음 포상까지 필요한 출석 체크: {u.reward_threshold}", reply_to_message_id=message_id)
                
                
            elif chat_info['message']['text'] == '/지급요청':
                try:
                    u = 유저.objects.get(텔레그램ID=user_id)
                except:
                    send_md2(bot, chat_id = chat_id, text = f"사용자 정보를 찾을 수 없습니다.", reply_to_message_id=message_id)
                    return JsonResponse({"ok": "POST request processed"})
                try:
                    if first_name != u.이름: 
                        u.이름 = first_name
                        u.save()
                except: pass
                send_md2(bot, chat_id = chat_id, text = f"포상 요청:\n유저 ID: {user_id}\n계급: {u.계급}\n전체 채팅 횟수: {u.채팅}\n보유 TRX: {u.TRX}", reply_to_message_id=message_id)
                
                
            elif chat_info['message']['text'] == '/코갤사령부가동':
                chat_member = bot.get_chat_member(chat_id=chat_id, user_id=user_id)
                if chat_member.status in ['administrator', 'creator']:
                    send_md2(bot, chat_id = chat_id, text = "코갤사령부가 가동되었습니다. 모든 시스템이 준비되었습니다!", reply_to_message_id=message_id)
                else: 
                    send_md2(bot, chat_id = chat_id, text = "관리자가 아닙니다 돌아가십시오", reply_to_message_id=message_id)      
            
            else:
                try:
                    u = 유저.objects.get(텔레그램ID=user_id)
                except:
                    send_md2(bot, chat_id = chat_id, text = f"출석 체크를 먼저 완료해야 합니다.", reply_to_message_id=message_id)
                    return JsonResponse({"ok": "POST request processed"})
                try: 
                    if first_name != u.이름: u.이름 = first_name
                except: pass
                if u.오늘출석:
                    if chat_info['message']['text'].isdecimal():
                        if len(가위바위보.objects.filter(텔레그램ID=user_id,TRX입력=False)) > 0:
                            bot2 = telegram.Bot(token = 가위바위보봇)
                            if  u.TRX < float(chat_info['message']['text']):
                                send_md2(bot2, chat_id = chat_id, text = f"{u.이름}님 잔고가 부족합니다. 현재 잔고: {u.TRX} TRX")
                                return JsonResponse({"ok": "POST request processed"})
                            tm = 가위바위보_타이머.objects.all()[0]
                            if len(가위바위보.objects.filter(TRX입력=True)) == 0:
                                kbb = 가위바위보.objects.filter(텔레그램ID=user_id,TRX입력=False)[0]
                                kbb.TRX입력 = True
                                kbb.TRX = int(chat_info['message']['text'])
                                kbb.save()
                                subprocess.Popen(["python3", "rps/rps_waiting.py","--id=" + str(kbb.id)], shell=False, stdin=None, stdout=None, stderr=None, close_fds=True)
                                send_md2(bot2, chat_id = chat_id, text = f"{u.이름}님이 {kbb.TRX} TRX를 걸고 매칭을 시작했습니다. {tm.매칭대기시간}초 안에 상대방이 나타나지 않으면 매칭이 종료됩니다.")
                                
                            elif len(가위바위보.objects.filter(TRX입력=True)) == 1:
                                kbb2 = 가위바위보.objects.filter(TRX입력=True)[0]
                                if kbb2.TRX == int(chat_info['message']['text']):
                                    kbb = 가위바위보.objects.filter(텔레그램ID=user_id,TRX입력=False)[0]
                                    kbb.TRX입력 = True
                                    kbb.TRX = int(chat_info['message']['text'])
                                    kbb.save()
                                    kbbs = 가위바위보.objects.filter(TRX입력=False)
                                    for k in kbbs:
                                        k.delete()
                                    subprocess.Popen(["python3", "rps/rps.py","--id1=" + str(kbb.id), "--id2="  + str(kbb2.id)], shell=False, stdin=None, stdout=None, stderr=None, close_fds=True)
                                    send_md2(bot2, chat_id = chat_id, 
                                                    text=(
                                                        f"{kbb2.이름} vs {u.이름}!\n\n"
                                                        f"각자 {kbb.TRX} TRX를 걸었습니다.\n\n"
                                                        f"가위, 바위, 보를 선택하세요.\n\n"
                                                        f"⚠️ {tm.가위바위보_선택시간}초 안에 선택하지 않으면 패배합니다!"
                                                    ),
                                                    reply_markup=create_rps_buttons())
                                else:
                                    send_md2(bot2, chat_id = chat_id, text = f"{u.이름}님, {kbb2.이름}님과 가위바위보 매칭을 성사시키려면 동일한 TRX갯수를 보상으로 걸어주세요. 현재 걸린 TRX: {kbb2.TRX} TRX")
                    else:    
                        u.이번주_채팅 = u.이번주_채팅 + 1
                        u.채팅 = u.채팅 + 1
                        kk = 계급.objects.all().order_by('채팅')
                        for i in range(len(kk)):
                            if kk[i].채팅 > u.채팅:
                                if kk[i-1] != u.계급:
                                    u.계급 = kk[i-1]
                                    send_md2(bot, chat_id = chat_id, text = f"{first_name}님, 축하합니다! 새로운 계급: {u.계급}!", reply_to_message_id=message_id)
                                break
                        
                        if random.random() < (u.계급.보상률 / 100):
                            u.TRX = u.TRX + 1
                            send_md2(bot, chat_id = chat_id, text = f"{first_name}님, {u.계급.보상률}% 확률로 1TRX 포상을 획득하셨습니다!", reply_to_message_id=message_id)
                else:
                    send_md2(bot, chat_id = chat_id, text = f"출석 체크를 먼저 완료해야 합니다.", reply_to_message_id=message_id)
                    return JsonResponse({"ok": "POST request processed"})
                u.save()
                
    except Exception as e:
        logging.error("error : " + str(e))  
        
    return JsonResponse({"ok": "POST request processed"})



@csrf_exempt
def game1callback(request):
    가위바위보봇 = "7532276504:AAF9YWcOyMSbsIkNhBf5Hhfsf5e9QXk54gA"
    answer = ((request.body).decode('utf-8'))
    chat_info = json.loads(answer)
    check = False
    try:
        if len(가위바위보.objects.filter(TRX입력=True)) == 2:
            kbbs = 가위바위보.objects.filter(TRX입력=True)
            for kbb in kbbs:
                if kbb.텔레그램ID == str(chat_info['callback_query']['from']['id']):
                    kbb.선택 = chat_info['callback_query']['data']
                    kbb.save()
                    check = True
                    break
            if check:
                chat_id = chat_info['callback_query']['message']['chat']['id']
                bot2 = telegram.Bot(token = 가위바위보봇)
                choice1 = kbbs[0].선택
                choice2 = kbbs[1].선택
                trx = kbbs[0].TRX
                if choice1 != 'None' and choice2 != 'None':
                    winning_cases = {
                    '가위': '보',
                    '바위': '가위',
                    '보': '바위'
                    }  
                    if choice1 == choice2:
                        kbb3 = 가위바위보.objects.create(텔레그램ID=kbbs[0].텔레그램ID, 이름=kbbs[0].이름, TRX입력=True, TRX=trx)
                        kbb4 = 가위바위보.objects.create(텔레그램ID=kbbs[1].텔레그램ID, 이름=kbbs[1].이름, TRX입력=True, TRX=trx)
                        kbbs[0].delete()
                        kbbs[1].delete()
                        subprocess.Popen(["python3", "rps/rps.py","--id1=" + str(kbb3.id), "--id2="  + str(kbb4.id)], shell=False, stdin=None, stdout=None, stderr=None, close_fds=True)
                        send_md2(bot2, chat_id=chat_id, text=f"무승부! {choice1} vs {choice2} - 다시 선택해 주세요.")
                        send_md2(bot2, chat_id=chat_id, text="무승부! 가위, 바위, 보를 다시 선택하세요.", reply_markup=create_rps_buttons())
                    elif winning_cases[choice1] == choice2:
                        winner = 유저.objects.get(텔레그램ID=kbbs[0].텔레그램ID)
                        looser = 유저.objects.get(텔레그램ID=kbbs[1].텔레그램ID)
                        winner.TRX = winner.TRX + float(trx)
                        looser.TRX = looser.TRX - float(trx)
                        winner.save()
                        looser.save()
                        send_md2(bot2, chat_id=chat_id, text=f"'{winner.이름}'님이 '{choice1}'로 승리하였습니다!\n\n'{looser.이름}'님은 '{choice2}'로 패배하였습니다.\n\n{trx} TRX가 '{winner.이름}'님에게 전달되었습니다.")
                        가위바위보.objects.all().delete()
                    else:
                        winner = 유저.objects.get(텔레그램ID=kbbs[1].텔레그램ID)
                        looser = 유저.objects.get(텔레그램ID=kbbs[0].텔레그램ID)
                        winner.TRX = winner.TRX + float(trx)
                        looser.TRX = looser.TRX - float(trx)
                        winner.save()
                        looser.save()
                        send_md2(bot2, chat_id=chat_id, text=f"'{winner.이름}'님이 '{choice2}'로 승리하였습니다!\n\n'{looser.이름}'님은 '{choice1}'로 패배하였습니다.\n\n{trx} TRX가 '{winner.이름}'님에게 전달되었습니다.")
                        가위바위보.objects.all().delete()
                    
                else:  
                    answer_cb_md2(
                            bot2,
                            callback_query_id=chat_info['callback_query']['id'],
                            text=f"{chat_info['callback_query']['data']} 선택 완료! 상대방의 선택을 기다리고 있습니다.",
                            show_alert=True
                        )
    except Exception as e: 
        logging.error("error : " + str(e))

    return JsonResponse({"ok": "POST request processed"})



@csrf_exempt
# 트레이딩게임 콜백 뷰 (버전: 1.0.0, 날짜: 2025-12-30)
def tradinggamecallback(request):
    트레이딩게임봇 = "6716341726:AAFrHEpW3xuUtSqEwQo41Xd7aRHfe6zYLEQ"
    answer = ((request.body).decode('utf-8'))
    chat_info = json.loads(answer)

    try:
        chat_info['message']
        k = 'ms'
    except Exception as e:
        k = 'cb'
    try:    
        bot = telegram.Bot(token = 트레이딩게임봇)
        if k == 'ms':
            chat_id = chat_info['message']['chat']['id']
            if str(chat_id) == '-1002301241304':
                user_id = str(chat_info['message']['from']['id'])
                first_name = chat_info['message']['from']['first_name']
                message_id = chat_info['message']['message_id']
                u = 유저.objects.get(텔레그램ID=user_id)
                
                if chat_info['message']['text'] == '/참가':
                    if len(트레이딩게임.objects.filter(진행중=True,베팅중=True)) > 0:
                        tg = 트레이딩게임.objects.filter(진행중=True,베팅중=True)[0]
                        if len(트레이딩게임_베팅.objects.filter(게임ID=tg.id,텔레그램ID=user_id)) == 0:
                            # 베팅 방향 버튼
                            direction_buttons = [
                                InlineKeyboardButton(" 📈양봉", callback_data='양봉'),
                                InlineKeyboardButton(" 📉음봉", callback_data='음봉')
                            ]
                            keyboard = [direction_buttons]
                            reply_markup = InlineKeyboardMarkup(keyboard)
                            send_md2(
                                bot,
                                chat_id=chat_id,
                                text=f"{first_name} {u.계급}님, 베팅 방향을 먼저 선택하세요",
                                reply_to_message_id=message_id,
                                reply_markup=reply_markup
                            )
                        else:
                            send_md2(bot, chat_id = chat_id, text = f"이미 참가하셨습니다. 다시 참가할 수 없습니다.", reply_to_message_id=message_id)
                    else:
                        send_md2(bot, chat_id = chat_id, text = f"베팅이 마감되었습니다. 다음 라운드를 기다려주세요.", reply_to_message_id=message_id)
                    
                elif chat_info['message']['text'] == '/행정반':
                    users = 유저.objects.all().order_by('-트레이딩게임_누적_승리')
                    rank = 0
                    prev_score = None
                    actual_rank = 0

                    for user in users:
                        actual_rank += 1
                        if user.트레이딩게임_누적_승리 != prev_score:
                            rank = actual_rank
                            prev_score = user.트레이딩게임_누적_승리

                        if user.텔레그램ID == user_id:
                            break
                    send_md2(bot, chat_id = chat_id, text = f"유저 : {first_name}\n계급 : {u.계급}\n보유 TRX : {u.TRX}\n누적 승리 : {u.트레이딩게임_누적_승리}\n누적 패배 : {u.트레이딩게임_누적_패배}\n연승 기록 : 🔥{u.트레이딩게임_연승}연승\n게임 랭킹 : {rank}위\n총 수익 : {u.트레이딩게임_총수익} TRX", reply_to_message_id=message_id)
                
                elif chat_info['message']['text'] == '/참가취소':
                    if len(트레이딩게임.objects.filter(진행중=True,베팅중=True)) > 0:
                        try: 
                            tg = 트레이딩게임.objects.filter(진행중=True,베팅중=True)[0]
                            tgb = 트레이딩게임_베팅.objects.get(게임ID=tg.id,텔레그램ID=user_id)
                            tgb.delete()
                            send_md2(bot, chat_id = chat_id, text = f"베팅이 취소되었습니다.", reply_to_message_id=message_id)
                        except: send_md2(bot, chat_id = chat_id, text = "아직 베팅을 하지 않았습니다. 취소할 베팅이 없습니다.", reply_to_message_id=message_id)
                            
                    else:
                        bot.sendMessage(chat_id = chat_id, text = f"베팅이 마감되었습니다. 다음 라운드를 기다려주세요.", parse_mode="HTML", reply_to_message_id=message_id)
                        
                
                elif chat_info['message']['text'] in ['/베팅내역', '/참가내역']:
                    if len(트레이딩게임.objects.filter(진행중=True)) > 0:
                        try: 
                            tg = 트레이딩게임.objects.filter(진행중=True)[0]
                            tgb = 트레이딩게임_베팅.objects.get(게임ID=tg.id,텔레그램ID=user_id)
                            send_md2(bot, chat_id = chat_id, text = f"{first_name} {u.계급}님 베팅 내역\n{tgb.방향} : {tgb.TRX} TRX", reply_to_message_id=message_id)
                        except: send_md2(bot, chat_id = chat_id, text = f"아직 베팅을 하지 않았습니다.", reply_to_message_id=message_id)
                            
                    else:
                        send_md2(bot, chat_id = chat_id, text = f"진행중인 게임이 없습니다. 다음 라운드를 기다려주세요.", reply_to_message_id=message_id)
                
                elif (chat_info['message']['text']).isdecimal():
                    if len(트레이딩게임.objects.filter(진행중=True,베팅중=True)) > 0:  
                        try: 
                            tg = 트레이딩게임.objects.filter(진행중=True,베팅중=True)[0]
                            tgb = 트레이딩게임_베팅.objects.get(게임ID=tg.id,텔레그램ID=user_id)
                            if u.TRX >= int(chat_info['message']['text']):  
                                if int(chat_info['message']['text']) > 100:
                                    send_md2(bot, chat_id = chat_id, text = f"100TRX 이하만 베팅 가능합니다.", reply_to_message_id=message_id) 
                                else:
                                    tgb.TRX = int(chat_info['message']['text'])
                                    tgb.save()
                                    send_md2(bot, chat_id = chat_id, text = f"{chat_info['message']['text']} TRX 선택을 완료했습니다. 베팅갯수를 선택해주세요.", reply_to_message_id=message_id)
                            else: 
                                send_md2(bot, chat_id = chat_id, text = f"잔액이 부족합니다.", reply_to_message_id=message_id) 
                        
                        except: 
                            send_md2(bot, chat_id = chat_id, text = "아직 참가를 하지 않았습니다.", reply_to_message_id=message_id)
                        
        elif k == 'cb':
            chat_id = chat_info['callback_query']['message']['chat']['id']
            user_id = str(chat_info['callback_query']['from']['id'])
            choice = chat_info['callback_query']['data']
            
            u = 유저.objects.get(텔레그램ID=user_id)
            if len(트레이딩게임.objects.filter(진행중=True,베팅중=True)) > 0:
                tg = 트레이딩게임.objects.filter(진행중=True,베팅중=True)[0]
                if choice == '양봉' or choice == '음봉':
                    try:
                        tgb = 트레이딩게임_베팅.objects.get(게임ID=tg.id, 텔레그램ID=user_id)
                        tgb.방향 = choice
                        tgb.save()
                    except 트레이딩게임_베팅.DoesNotExist:
                        트레이딩게임_베팅.objects.create(게임ID=tg.id, 텔레그램ID=user_id, 방향=choice)

                    amount_buttons = [
                        InlineKeyboardButton(f"{i} TRX", callback_data=f"{i} TRX")
                        for i in range(1, 21)
                    ]
                    amount_rows = [amount_buttons[i:i + 4] for i in range(0, 20, 4)]
                    reply_markup = InlineKeyboardMarkup(amount_rows)

                    answer_cb_md2(
                        bot,
                        callback_query_id=chat_info['callback_query']['id'],
                        text=f"{choice} 선택 완료!",
                        show_alert=True
                    )

                    time.sleep(0.5)

                    send_md2(
                        bot,
                        chat_id=chat_id,
                        text=f"{u.이름} {u.계급}님, 베팅 금액을 선택해주세요",
                        reply_markup=reply_markup
                    )

                elif choice.endswith(' TRX'):
                    amount = int(choice.split()[0])
                    if u.TRX >= amount:
                        try:
                            tgb = 트레이딩게임_베팅.objects.get(게임ID=tg.id,텔레그램ID=user_id)
                            tgb.TRX = amount
                            tgb.save()
                            if tgb.방향:
                                send_md2(
                                    bot,
                                    chat_id=chat_id,
                                    text=f"{u.이름} {u.계급}님이 {tgb.방향}에 {tgb.TRX} TRX를 베팅했습니다!"
                                )
                        except 트레이딩게임_베팅.DoesNotExist:
                            트레이딩게임_베팅.objects.create(
                                게임ID=tg.id,텔레그램ID=user_id,TRX=amount
                            )
                    else:
                        answer_cb_md2(
                            bot,
                            callback_query_id=chat_info['callback_query']['id'],
                            text="잔액이 부족합니다.",
                            show_alert=True
                        )
                        return JsonResponse({"ok": "POST request processed"})
                
                answer_cb_md2(
                                    bot,
                                    callback_query_id=chat_info['callback_query']['id'],
                                    text=f"{choice} 선택을 완료했습니다.",
                                    show_alert=True
                                )
            elif len(트레이딩게임.objects.filter(진행중=True)) > 0:
                answer_cb_md2(
                                    bot,
                                    callback_query_id=chat_info['callback_query']['id'],
                                    text=f"베팅이 마감되었습니다. 다음 라운드를 기다려주세요.",
                                    show_alert=True
                                )
    except Exception as e: 
        logging.error("error : " + str(e))
        
    return JsonResponse({"ok": "POST request processed"})


@csrf_exempt
def kimp(request, key):
    return JsonResponse({"res": kakao_command(key)})
