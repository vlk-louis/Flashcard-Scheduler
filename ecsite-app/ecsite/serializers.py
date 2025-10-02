from rest_framework import serializers
from .models import CartItem, Item, Cart


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = ["id", "name", "price", "quantity"]


class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = ["item", "quantity"]


class CartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cart
        fields = ["items"]
