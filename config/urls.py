"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from store.views import product_list, product_detail, cart_add, cart_remove, cart_detail, checkout
from django.conf import settings
from django.conf.urls.static import static

# DRF router
from rest_framework.routers import DefaultRouter
from store.api import CategoryViewSet, ProductViewSet, SKUViewSet

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'skus', SKUViewSet, basename='sku')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', product_list, name='home'),
    path('products/<slug:slug>/', product_detail, name='product_detail'),

    path('cart/', cart_detail, name='cart_detail'),
    path('cart/add/<int:sku_id>/', cart_add, name='cart_add'),
    path('cart/remove/<int:sku_id>/', cart_remove, name='cart_remove'),
    path('checkout/', checkout, name='checkout'),

    path('api/', include(router.urls)),  # 👈 API lives here
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


