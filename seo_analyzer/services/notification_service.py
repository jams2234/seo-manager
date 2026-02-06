"""
Notification Service
분석 완료, 제안, 긴급 이슈 알림 발송

Features:
- Telegram 알림
- 이메일 알림 (선택)
- WebSocket 실시간 알림 (선택)
"""
import logging
from typing import Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """
    사용자 알림 서비스

    지원 채널:
    - Telegram (기본)
    - Email (high priority)
    - WebSocket (실시간)
    """

    def __init__(self):
        self.telegram_enabled = self._check_telegram()
        self.email_enabled = self._check_email()

    def _check_telegram(self) -> bool:
        """텔레그램 봇 설정 확인"""
        return hasattr(settings, 'TELEGRAM_BOT_TOKEN') and bool(settings.TELEGRAM_BOT_TOKEN)

    def _check_email(self) -> bool:
        """이메일 설정 확인"""
        return hasattr(settings, 'EMAIL_HOST') and bool(settings.EMAIL_HOST)

    def notify_analysis_complete(self, domain, run) -> bool:
        """
        분석 완료 알림

        Args:
            domain: Domain 모델 인스턴스
            run: AIAnalysisRun 모델 인스턴스

        Returns:
            알림 발송 성공 여부
        """
        completed_at = run.completed_at.strftime('%Y-%m-%d %H:%M') if run.completed_at else 'N/A'

        message = f"""
✅ AI SEO 분석 완료

📊 도메인: {domain.domain_name}
⏰ 분석 시간: {completed_at}
💡 제안 수: {run.suggestions_count}개
🔍 인사이트: {run.insights_count}개

자세한 결과는 대시보드에서 확인하세요.
"""

        return self._send_notification(
            user=getattr(domain, 'owner', None),
            message=message,
            priority='normal'
        )

    def notify_critical_issue(self, domain, issue) -> bool:
        """
        긴급 이슈 알림

        Args:
            domain: Domain 모델 인스턴스
            issue: SEOIssue 모델 인스턴스

        Returns:
            알림 발송 성공 여부
        """
        page_url = issue.page.url if issue.page else 'N/A'

        message = f"""
⚠️ 긴급 SEO 이슈 감지

🌐 도메인: {domain.domain_name}
📝 이슈: {issue.title}
🔴 심각도: {issue.severity}
📄 페이지: {page_url}

즉시 조치가 필요합니다.
"""

        return self._send_notification(
            user=getattr(domain, 'owner', None),
            message=message,
            priority='high'
        )

    def notify_suggestion(self, domain, suggestion) -> bool:
        """
        새 제안 알림

        Args:
            domain: Domain 모델 인스턴스
            suggestion: AISuggestion 모델 인스턴스

        Returns:
            알림 발송 성공 여부
        """
        message = f"""
💡 새로운 SEO 개선 제안

🌐 도메인: {domain.domain_name}
📝 제안: {suggestion.title}
⭐ 우선순위: {'높음' if suggestion.priority == 1 else '중간' if suggestion.priority == 2 else '낮음'}
📈 예상 효과: {suggestion.expected_impact or 'N/A'}

대시보드에서 제안을 확인하고 적용하세요.
"""

        return self._send_notification(
            user=getattr(domain, 'owner', None),
            message=message,
            priority='normal'
        )

    def notify_learning_complete(self, domain, learning_state) -> bool:
        """
        학습 동기화 완료 알림

        Args:
            domain: Domain 모델 인스턴스
            learning_state: AILearningState 모델 인스턴스

        Returns:
            알림 발송 성공 여부
        """
        message = f"""
🧠 AI 학습 동기화 완료

🌐 도메인: {domain.domain_name}
📄 동기화 페이지: {learning_state.pages_synced}개
🔄 업데이트된 임베딩: {learning_state.embeddings_updated}개
✅ 상태: {learning_state.sync_status}
"""

        return self._send_notification(
            user=getattr(domain, 'owner', None),
            message=message,
            priority='low'
        )

    def _send_notification(
        self,
        user,
        message: str,
        priority: str = 'normal',
    ) -> bool:
        """
        알림 발송

        Args:
            user: User 모델 인스턴스 (선택)
            message: 알림 메시지
            priority: 'low', 'normal', 'high'

        Returns:
            발송 성공 여부
        """
        success = False

        # 텔레그램
        if self.telegram_enabled:
            if self._send_telegram(user, message):
                success = True

        # 이메일 (high priority만)
        if self.email_enabled and priority == 'high':
            if user and hasattr(user, 'email') and user.email:
                if self._send_email(user.email, message):
                    success = True

        # WebSocket (실시간)
        if self._send_websocket(user, message):
            success = True

        return success

    def _send_telegram(self, user, message: str) -> bool:
        """텔레그램 메시지 발송"""
        if not self.telegram_enabled:
            return False

        try:
            # user.telegram_chat_id가 있는 경우에만 발송
            chat_id = getattr(user, 'telegram_chat_id', None) if user else None

            if not chat_id:
                # 기본 chat_id 사용 (설정에서)
                chat_id = getattr(settings, 'TELEGRAM_DEFAULT_CHAT_ID', None)

            if not chat_id:
                logger.debug("No Telegram chat_id available")
                return False

            # 텔레그램 봇 API 사용
            import requests

            token = settings.TELEGRAM_BOT_TOKEN
            url = f"https://api.telegram.org/bot{token}/sendMessage"

            response = requests.post(url, data={
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML',
            }, timeout=10)

            if response.status_code == 200:
                logger.info(f"Telegram notification sent to {chat_id}")
                return True
            else:
                logger.warning(f"Telegram API error: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")
            return False

    def _send_email(self, email: str, message: str) -> bool:
        """이메일 발송"""
        if not self.email_enabled:
            return False

        try:
            from django.core.mail import send_mail

            send_mail(
                subject='[SEO Analyzer] 알림',
                message=message,
                from_email=None,  # DEFAULT_FROM_EMAIL 사용
                recipient_list=[email],
                fail_silently=False,
            )
            logger.info(f"Email notification sent to {email}")
            return True

        except Exception as e:
            logger.error(f"Email notification failed: {e}")
            return False

    def _send_websocket(self, user, message: str) -> bool:
        """WebSocket 실시간 알림"""
        try:
            # Django Channels 사용 시
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()
            if channel_layer and user:
                user_id = getattr(user, 'id', None)
                if user_id:
                    async_to_sync(channel_layer.group_send)(
                        f"user_{user_id}",
                        {
                            'type': 'notification',
                            'message': message,
                        }
                    )
                    logger.debug(f"WebSocket notification sent to user_{user_id}")
                    return True

        except ImportError:
            # Django Channels가 설치되지 않은 경우
            pass
        except Exception as e:
            logger.debug(f"WebSocket notification skipped: {e}")

        return False


# 싱글톤 인스턴스
_notification_service_instance = None


def get_notification_service() -> NotificationService:
    """알림 서비스 싱글톤 인스턴스 반환"""
    global _notification_service_instance
    if _notification_service_instance is None:
        _notification_service_instance = NotificationService()
    return _notification_service_instance
