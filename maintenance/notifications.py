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
        return response.status_code == 200
    except Exception as e:
        logger.error(f"LINE Notify error: {str(e)}")
        return False


def send_notification(user_id, title, message, maintenance_request):
    """
    ส่งการแจ้งเตือนผ่านหลายช่องทาง: Email, LINE Notify, และ In-app notification
    """
    from .models import User, Notification  # Import here to avoid circular import

    user = User.objects.get(id=user_id)

    # บันทึก In-app notification
    Notification.objects.create(
        user=user,
        title=title,
        message=message,
        maintenance_request=maintenance_request,
    )

    # ส่ง Email
    if user.email:
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
            html_message=email_html
        )

    # ส่ง LINE Notify (ถ้ามีการตั้งค่า LINE Token)
    if hasattr(user, 'line_token') and user.line_token:
        send_line_notify(user.line_token, f'{title}\n{message}')
