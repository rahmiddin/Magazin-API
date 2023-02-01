from rest_framework import serializers
from .models import User, Category, Contact, Shop, Order, Product


class UserSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ('email', 'password', 'type', 'last_name', 'first_name')
        read_only_fields = ('id',)

