import os
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.db import IntegrityError
from django.db.models import Sum, F, Q
from django.http import JsonResponse
from django.core.files.storage import default_storage
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from .seralizers import UserSerializer, OrderSerializer, OrderItemSerializer, ProductInfoSerializer, \
    CategorySerializer, ShopSerializer
from .models import User, ConfirmEmailToken, Category, Shop, Product, ProductInfo, ProductParameter, Parameter, \
    Order, OrderItem
from backend.signals import new_user_registered
from rest_framework.authtoken.models import Token
import yaml
from ujson import loads, load
# from json import loads


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


class CategoryView(ListAPIView):
    """To get categories"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ShopView(ListAPIView):
    """To get a shop"""
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer



class BasketView(APIView):
    """
    Класс для работы с корзиной пользователя
    """

    # получить корзину
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

    # редактировать корзину
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_sting = request.data.get('items')
        if items_sting:
            try:
                items_dict = loads(items_sting)
            except ValueError:
                JsonResponse({'Status': False, 'Errors': 'Неверный формат запроса'})
            else:
                basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
                objects_created = 0
                for order_item in items_dict:
                    product_info = ProductInfo.objects.get(external_id=order_item['id']).id
                    order_item.update({'order': basket.id, 'product_info': product_info})
                    serializer = OrderItemSerializer(data=order_item)
                    if serializer.is_valid():
                        try:
                            serializer.save()
                        except IntegrityError as error:
                            return JsonResponse({'Status': False, 'Errors1': str(error)})
                        else:
                            objects_created += 1

                    else:

                        JsonResponse({'Status': False, 'Errors': serializer.errors})

                return JsonResponse({'Status': True, 'Создано объектов': objects_created})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    # удалить товары из корзины
    def delete(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_sting = request.data.get('items')
        if items_sting:
            items_list = items_sting.split(',')
            basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
            query = Q()
            objects_deleted = False
            for order_item_id in items_list:
                print(order_item_id)
                if order_item_id.isdigit():
                    query = query | Q(order_id=basket.id, id=order_item_id)
                    objects_deleted = True

            if objects_deleted:
                deleted_count = OrderItem.objects.filter(query).delete()[0]
                return JsonResponse({'Status': True, 'Удалено объектов': deleted_count})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    # добавить позиции в корзину
    def put(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_sting = request.data.get('items')
        if items_sting:
            try:
                items_dict = loads(items_sting)
            except ValueError:
                return JsonResponse({'Status': False, 'Errors': 'Неверный формат запроса'})
            else:
                basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
                objects_updated = 0
                for order_item in items_dict:
                    print(order_item)
                    if type(order_item['id']) == int and type(order_item['quantity']) == int:
                        obj = OrderItem.objects.filter(order_id=basket.id, id=order_item['id'])
                        print(obj)
                        objects_updated += OrderItem.objects.filter(order_id=basket.id, id=order_item['id']).update(
                            quantity=order_item['quantity'])
                        print(objects_updated)
                return JsonResponse({'Status': True, 'Обновлено объектов': objects_updated})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class ProductInfoView(APIView):
    """A class for searching for products"""
    def get(self, request, *args, **kwargs):

        query = Q(shop__state=True)
        shop_id = request.query_params.get('shop_id')
        category_id = request.query_params.get('category_id')

        if shop_id:
            query = query & Q(shop_id=shop_id)

        if category_id:
            query = query & Q(product__category_id=category_id)

        queryset = ProductInfo.objects.filter(
            query).select_related(
            'shop', 'product__category').prefetch_related(
            'product_parameters__parameter').distinct()

        serializer = ProductInfoSerializer(queryset, many=True)

        return Response(serializer.data)