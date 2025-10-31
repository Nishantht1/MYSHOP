from django.db import models
from django.utils.text import slugify
from django.db import transaction

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class Category(TimeStampedModel):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Categories"   # ✅ Fix plural name


    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Product(TimeStampedModel):
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    description = models.TextField(blank=True)
    price_cents = models.PositiveIntegerField(default=0)  # store money as integer cents
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)

    @property
    def price(self):
        # dollars for display, since we store cents in the DB
        return self.price_cents / 100
    
    @property
    def total_stock_available(self):
        # Sum of related SKUs’ available stock
        return sum(s.stock_available for s in self.skus.all())



    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class SKU(TimeStampedModel):
    """Sellable stock-keeping unit (e.g., a particular variant)."""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='skus')
    code = models.CharField(max_length=64, unique=True)
    stock_on_hand = models.IntegerField(default=0)     # physical stock
    stock_reserved = models.IntegerField(default=0)    # in carts/orders
    is_active = models.BooleanField(default=True)
    

    def can_fulfill(self, qty: int) -> bool:
        return qty > 0 and self.stock_on_hand - self.stock_reserved >= qty
    
    def deduct(self, qty: int):
        """Reduce on-hand stock by qty. Assume validation already done."""
        self.stock_on_hand = max(0, self.stock_on_hand - qty)
        self.save(update_fields=["stock_on_hand", "updated_at"])

    
    class Meta:
        verbose_name_plural = "SKUs"

    @property
    def stock_available(self):
        return max(0, self.stock_on_hand - self.stock_reserved)

    def __str__(self):
        return f"{self.product.name} — {self.code}"


class OrderStatus(models.TextChoices):
    NEW = "NEW", "New"
    PAID = "PAID", "Paid"
    SHIPPED = "SHIPPED", "Shipped"
    CANCELED = "CANCELED", "Canceled"

class Order(TimeStampedModel):
    customer_name = models.CharField(max_length=160)
    email = models.EmailField()
    address_line = models.CharField(max_length=200)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    status = models.CharField(max_length=12, choices=OrderStatus.choices, default=OrderStatus.NEW)
    total_cents = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Order #{self.id} — {self.customer_name}"

class OrderItem(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    sku = models.ForeignKey(SKU, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    price_cents = models.PositiveIntegerField()      # price snapshot at purchase time
    line_total_cents = models.PositiveIntegerField() # price_cents * quantity

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
