from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.dispatch import receiver, Signal
from backend.models import ConfirmEmailToken, User

new_user_registered = Signal(
    'user_id',
)


@receiver(new_user_registered)
def new_user_registered_signal(user_id: int, **kwargs):
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