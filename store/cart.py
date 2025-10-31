from decimal import Decimal
from django.conf import settings
from store.models import SKU

CART_SESSION_ID = "cart"

class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(CART_SESSION_ID)
        if cart is None:
            cart = self.session[CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, sku_id: int, quantity: int = 1, max_available: int = None):
        sku_key = str(sku_id)
        current_qty = self.cart.get(sku_key, 0)
        new_qty = current_qty + quantity
        if max_available is not None:
            new_qty = max(0, min(new_qty, max_available))
        self.cart[sku_key] = new_qty
        self.session.modified = True

    def set(self, sku_id: int, quantity: int, max_available: int = None):
        sku_key = str(sku_id)
        qty = quantity
        if max_available is not None:
            qty = max(0, min(qty, max_available))
        if qty <= 0:
            self.cart.pop(sku_key, None)
        else:
            self.cart[sku_key] = qty
        self.session.modified = True

    def remove(self, sku_id: int):
        sku_key = str(sku_id)
        if sku_key in self.cart:
            del self.cart[sku_key]
            self.session.modified = True

    def clear(self):
        self.session[CART_SESSION_ID] = {}
        self.session.modified = True

    def items(self):
        """Yield cart line items with SKU, product, price, etc."""
        sku_ids = [int(k) for k in self.cart.keys()]
        skus = SKU.objects.select_related("product").filter(id__in=sku_ids)
        sku_map = {s.id: s for s in skus}
        for key, qty in self.cart.items():
            sid = int(key)
            sku = sku_map.get(sid)
            if not sku:
                continue
            product = sku.product
            price = Decimal(product.price_cents) / Decimal(100)
            line_total = price * qty
            yield {
                "sku": sku,
                "product": product,
                "qty": qty,
                "price": price,
                "line_total": line_total,
                "available": sku.stock_available,
            }

    def total(self):
        from decimal import Decimal
        t = Decimal(0)
        for it in self.items():
            t += it["line_total"]
        return t
