from django.contrib import admin
from django.urls import path, include
from .views import RegisterAccount, ConfirmAccount, LoginAccount

urlpatterns = [
    path('user/register', RegisterAccount.as_view(), name='user_register'),
    path('user/login', LoginAccount.as_view(), name='user_login'),
    path('user/register/confirm', ConfirmAccount.as_view(), name='user-register-confirm'),
]
