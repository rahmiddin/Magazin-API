from django.test import TestCase
import json
from .models import User, ConfirmEmailToken
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from rest_framework import status
from .seralizers import UserSerializer


class RegistrationTestCase(APITestCase):

    def test_registration(self):
        data = {
            "last_name": "test",
            "first_name": "test",
            "password": "wwefan123",
            "type": "buyer",
            "email": "gaha@bk.ru",
        }
        response = self.client.post(reverse('user_register'), data=data, format='json')
        self.assertEqual(response.content, b'{"status": true}')

    def test_confirm_account(self):
        user = User.objects.create(id=999, last_name="test", first_name="test", password="wwefan123",
                                   type="buyer", email="gaha@bk.ru", )
        token = ConfirmEmailToken.objects.create(user=user, key='testkey')

        data = {
            'email': 'gaha@bk.ru',
            'token': 'testkey'
        }
        response = self.client.post(reverse('user-register-confirm'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, b'{"Status": true}')




