from rest_framework import serializers
from .models import Category, Product, SKU

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'is_active']

class SKUSerializer(serializers.ModelSerializer):
    stock_available = serializers.IntegerField(read_only=True)

    class Meta:
        model = SKU
        fields = ['id', 'code', 'stock_on_hand', 'stock_reserved', 'stock_available', 'is_active']

class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    image_url = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    skus = SKUSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description',
            'price_cents', 'price', 'is_active',
            'image_url', 'category', 'skus'
        ]

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            url = obj.image.url
            return request.build_absolute_uri(url) if request else url
        return None

    def get_price(self, obj):
        return obj.price_cents / 100.0
