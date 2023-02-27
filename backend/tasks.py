from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from .models import ConfirmEmailToken
from django.conf import settings
from .models import User


@shared_task()
def new_user_registered(user_id: int):
    """Send email confirmation"""
    # send an e-mail to the user
    token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user_id)

    msg = EmailMultiAlternatives(
        # title:
        f"Password Reset Token for {token.user.email}",
        # message:
        token.key,
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [token.user.email]
    )

    msg.send()


@shared_task()
def new_order(user_id: int):
    """we send an email when the order status changes"""
    # send an e-mail to the user
    user = User.objects.get(id=user_id)

    msg = EmailMultiAlternatives(
        # title:
        f"Обновление статуса заказа",
        # message:
        'Заказ сформирован',
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [user.email]
    )
    msg.send()
