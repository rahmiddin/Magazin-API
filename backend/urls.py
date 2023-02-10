from django.urls import path
from .views import RegisterAccount, ConfirmAccount, LoginAccount, PartnerUpdate, BasketView

urlpatterns = [
    path('user/register', RegisterAccount.as_view(), name='user_register'),
    path('user/login', LoginAccount.as_view(), name='user_login'),
    path('user/register/confirm', ConfirmAccount.as_view(), name='user-register-confirm'),
    path('partner/update', PartnerUpdate.as_view(), name='partner-update'),
    path('basket', BasketView.as_view(), name='basket')
]
