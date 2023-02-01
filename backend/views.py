from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.http import JsonResponse
from django.shortcuts import render
from rest_framework.views import APIView
from .seralizers import UserSerializer
from .models import User, ConfirmEmailToken
from backend.signals import new_user_registered
from rest_framework.authtoken.models import Token


# Create your views here.


class RegisterAccount(APIView):

    def post(self, request, *args, **kwargs):

        if {'email', 'password', 'type', 'last_name', 'first_name'}.issubset(request.data):
            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                errors_array = []
                for item in password_error:
                    errors_array.append(item)
                return JsonResponse({'status': False, 'Errors': {'password': errors_array}})
            else:
                user_serializer = UserSerializer(data=request.data)
                if user_serializer.is_valid():
                    user = user_serializer.save()
                    user.set_password(request.data['password'])
                    user.save()
                    new_user_registered.send(sender=self.__class__, user_id=user.id)
                    return JsonResponse({'status': True})
                else:
                    return JsonResponse({'status': False, 'Errors': user_serializer.errors})
        return JsonResponse({'status': False, 'Errors': 'не указаны все аргументы'})


class ConfirmAccount(APIView):

    def post(self, request, *args, **kwargs):

        if {'email', 'token'}.issubset(request.data):

            token = ConfirmEmailToken.objects.filter(user__email=request.data['email'],
                                                     key=request.data['token']).first()

            if token:
                token.user.is_active = True
                token.user.save()
                token.delete()
                return JsonResponse({'Status': True})
            else:
                return JsonResponse({'Status': False, 'Errors': 'Неправильно указан токен или email'})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class LoginAccount(APIView):
    """
    Класс для авторизации пользователей
    """
    # Авторизация методом POST
    def post(self, request, *args, **kwargs):

        if {'email', 'password'}.issubset(request.data):
            user = authenticate(request, username=request.data['email'], password=request.data['password'])

            if user is not None:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)

                    return JsonResponse({'Status': True, 'Token': token.key})

            return JsonResponse({'Status': False, 'Errors': 'Не удалось авторизовать'})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


