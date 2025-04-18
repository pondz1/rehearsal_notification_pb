from django.core.mail import send_mail
from django.conf import settings
from django.db.backends.utils import logger
from django.template.loader import render_to_string
import requests

def send_line_notify(token, message):
    """
    ส่งการแจ้งเตือนผ่าน LINE Notify
    """
    url = 'https://notify-api.line.me/api/notify'
    headers = {'Authorization': f'Bearer {token}'}
    payload = {'message': message}

    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()  # เพิ่มการตรวจสอบ HTTP errors
        return True
    except requests.RequestException as e:
        logger.error(f"LINE Notify error: {str(e)}")
        return False

def send_notification(user_id, title, message, maintenance_request=None):
    """
    ส่งการแจ้งเตือนตามการตั้งค่าของผู้ใช้
    """
    from .models import User, Notification  # Import here to avoid circular import

    try:
        user = User.objects.select_related('userprofile').get(id=user_id)
        notification_preference = user.userprofile.notification_preferences

        # บันทึก In-app notification เสมอ
        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            maintenance_request=maintenance_request,
        )

        # ตรวจสอบการตั้งค่าการแจ้งเตือน
        if notification_preference == 'NONE':
            return True

        success = True

        # ส่งอีเมลถ้าตั้งค่าไว้
        if notification_preference in ['ALL', 'EMAIL'] and user.email:
            success &= send_email_notification(user, title, message)

        # ส่ง LINE ถ้าตั้งค่าไว้
        if notification_preference in ['ALL', 'LINE'] and user.userprofile.line_token:
            success &= send_line_notify(user.userprofile.line_token, f'{title}\n{message}')

        return success

    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return False
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")
        return False

def send_email_notification(user, title, message):
    """
    ส่งการแจ้งเตือนทางอีเมล
    """
    try:
        context = {
            'user': user,
            'title': title,
            'message': message
        }

        email_html = render_to_string('emails/notification.html', context)
        email_text = render_to_string('emails/notification.txt', context)

        send_mail(
            subject=f'[แจ้งเตือน] {title}',
            message=email_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=email_html,
            fail_silently=False
        )
        return True
    except Exception as e:
        logger.error(f"Email sending error: {str(e)}")
        return False
