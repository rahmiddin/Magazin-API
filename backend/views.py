import os
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.db import IntegrityError
from django.db.models import Sum, F
from django.http import JsonResponse
from django.core.files.storage import default_storage
from rest_framework.response import Response
from rest_framework.views import APIView
from .seralizers import UserSerializer, OrderSerializer, OrderItemSerializer, ProductInfoSerializer
from .models import User, ConfirmEmailToken, Category, Shop, Product, ProductInfo, ProductParameter, Parameter, \
    Order, OrderItem
from backend.signals import new_user_registered
from rest_framework.authtoken.models import Token
import yaml
from ujson import loads, load


class RegisterAccount(APIView):
    """ Class for user registration"""

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
    """Account verification class"""

    def post(self, request, *args, **kwargs) -> JsonResponse:

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
    """Class for user authorization"""

    def post(self, request, *args, **kwargs):

        if {'email', 'password'}.issubset(request.data):
            user = authenticate(request, username=request.data['email'], password=request.data['password'])

            if user is not None:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)

                    return JsonResponse({'Status': True, 'Token': token.key})

            return JsonResponse({'Status': False, 'Errors': 'Не удалось авторизовать'})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerUpdate(APIView):
    """Class for updating the list of products"""

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        file = request.FILES.get('file')
        path = default_storage.save('tmp/data.yaml', ContentFile(file.read()))

        with open('tmp/data.yaml', 'r', encoding='utf-8') as stream:
            data = yaml.safe_load(stream)
            shop, _ = Shop.objects.get_or_create(name=data['shop'], user_id=request.user.id)
            for item in data['categories']:
                category, _ = Category.objects.get_or_create(id=item['id'], name=item['name'])
                category.shops.add(shop.id)
                category.save()

            for item in data['goods']:
                product_object, _ = Product.objects.get_or_create(name=item['name'], category_id=item['category'])
                product_info, _ = ProductInfo.objects.get_or_create(product_id=product_object.id,
                                                                    external_id=item['id'],
                                                                    model=item['model'],
                                                                    price=item['price'],
                                                                    price_rrc=item['price_rrc'],
                                                                    quantity=item['quantity'],
                                                                    shop_id=shop.id)
                for name, value in item['parameters'].items():
                    parameter_object, _ = Parameter.objects.get_or_create(name=name)
                    product_parameter, _ = ProductParameter.objects.get_or_create(product_info_id=product_info.id,
                                                                                  parameter_id=parameter_object.id,
                                                                                  value=value)
                stream.close()
            default_storage.delete(path)
            return JsonResponse({'Status': True})


class BasketView(APIView):
    """Class for working with the user's shopping cart """

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        item = request.data.get('item')
        print(item)
        if {'item', 'quantity'}.issubset(request.data):
            try:
                product = Product.objects.get(name=item).id
            except ObjectDoesNotExist:
                return JsonResponse({'Status': False, 'Error': 'Такой товар не сушествует'}, status=403)
            else:
                product_info = ProductInfo.objects.get(product_id=product)
                order, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
                item_create, _ = OrderItem.objects.get_or_create(order_id=order.id, id=product,
                                                                 product_info=product_info,
                                                                 quantity=request.data['quantity'])
                return JsonResponse({'Status': True})
        else:
            return JsonResponse({'Status': False, 'Error': 'Не указаны все необходимые аргументы'}, status=403)

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        basket = Order.objects.filter(
            user_id=request.user.id, state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        serializer = OrderSerializer(basket, many=True)
        return Response(serializer.data)

    def put(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        item = request.data.get('item')

        if item:
            try:
                item_dict = loads(item)
            except ValueError:
                JsonResponse({'Status': False, 'Errors': 'Неверный формат запроса'})
            else:
                order, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
                item_update = 0
                for product in item_dict:
                    if type(product['id']) == int and type(product['quantity']) == int:
                        item_update += OrderItem.objects.filter(order_id=order.id, id=product['id']).update(
                                                                        quantity=product['quantity'])
                    return JsonResponse({'Status': True, 'Обновлено объектов': item_update})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})
