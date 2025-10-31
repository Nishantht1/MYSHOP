from django.contrib import admin, messages
from django.db import transaction

from .models import Category, Product, SKU, Order, OrderItem, OrderStatus


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}

    class Meta:
        verbose_name_plural = "Categories"


class SKUInline(admin.TabularInline):
    model = SKU
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price_cents", "is_active", "created_at")
    list_filter = ("category", "is_active")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [SKUInline]


@admin.register(SKU)
class SKUAdmin(admin.ModelAdmin):
    list_display = ("code", "product", "stock_on_hand", "stock_reserved", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "product__name")

    class Meta:
        verbose_name_plural = "SKUs"


# ---- Orders ----

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "sku", "quantity", "price_cents", "line_total_cents")


@admin.action(description="Cancel selected orders and restock items")
def cancel_and_restock(modeladmin, request, queryset):
    updated = 0
    with transaction.atomic():
        qs = queryset.select_related().prefetch_related("items__sku")
        for order in qs:
            if order.status == OrderStatus.CANCELED:
                continue
            # restock
            for item in order.items.all():
                sku = item.sku
                sku.stock_on_hand = sku.stock_on_hand + item.quantity
                sku.save(update_fields=["stock_on_hand", "updated_at"])
            # mark canceled
            order.status = OrderStatus.CANCELED
            order.save(update_fields=["status", "updated_at"])
            updated += 1
    messages.success(request, f"Canceled and restocked {updated} order(s).")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer_name", "email", "status", "total_cents", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("customer_name", "email")
    inlines = [OrderItemInline]
    actions = [cancel_and_restock]
