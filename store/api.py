from rest_framework import viewsets, mixins
from rest_framework.permissions import AllowAny
from .models import Category, Product, SKU
from .serializers import CategorySerializer, ProductSerializer, SKUSerializer

class PublicReadOnly(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]

class CategoryViewSet(PublicReadOnly):
    queryset = Category.objects.filter(is_active=True).order_by('name')
    serializer_class = CategorySerializer

class ProductViewSet(PublicReadOnly):
    queryset = (
        Product.objects.filter(is_active=True)
        .select_related('category')
        .prefetch_related('skus')
        .order_by('name')
    )
    serializer_class = ProductSerializer
    lookup_field = 'slug'  # allow /products/<slug>/

class SKUViewSet(PublicReadOnly):
    queryset = SKU.objects.filter(is_active=True).select_related('product').order_by('code')
    serializer_class = SKUSerializer
