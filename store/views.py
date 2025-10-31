from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_http_methods, require_POST

from .models import Category, Product, SKU, Order, OrderItem
from .cart import Cart


# -------- Catalog & Product Detail --------

def product_list(request):
    products = (
        Product.objects
        .filter(is_active=True)
        .select_related('category')
        .prefetch_related('skus')
        .order_by('name')
    )
    return render(request, 'store/product_list.html', {'products': products})


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related('category').prefetch_related('skus'),
        slug=slug,
        is_active=True
    )
    return render(request, 'store/product_detail.html', {'p': product})


# -------- Cart --------

@require_POST
def cart_add(request, sku_id: int):
    sku = get_object_or_404(SKU.objects.select_related("product"), id=sku_id, is_active=True)
    try:
        qty = int(request.POST.get("qty", 1))
    except ValueError:
        qty = 1
    if qty <= 0:
        messages.error(request, "Quantity must be positive.")
        return redirect("product_detail", slug=sku.product.slug)

    cart = Cart(request)
    cart.add(sku.id, qty, max_available=sku.stock_available)  # clamp to available
    messages.success(request, f"Added {qty} × {sku.code} to cart.")
    return redirect("cart_detail")


def cart_remove(request, sku_id: int):
    cart = Cart(request)
    cart.remove(sku_id)
    messages.info(request, "Item removed from cart.")
    return redirect("cart_detail")


def cart_detail(request):
    cart = Cart(request)
    return render(request, "store/cart_detail.html", {"cart": cart})


# -------- Checkout (transactional stock deduction) --------

@require_http_methods(["GET", "POST"])
def checkout(request):
    cart = Cart(request)

    # Quick empty check
    if not any(True for _ in cart.items()):
        return render(request, "store/checkout_empty.html", {})

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        email = (request.POST.get("email") or "").strip()
        address = (request.POST.get("address") or "").strip()
        city = (request.POST.get("city") or "").strip()
        state = (request.POST.get("state") or "").strip()
        postal = (request.POST.get("postal") or "").strip()

        if not name or not email or not address:
            messages.error(request, "Name, email and address are required.")
            return render(request, "store/checkout.html", {"cart": cart})

        # Build a simple snapshot of lines
        line_reqs = []
        total_cents = 0
        for it in cart.items():
            price_cents = int(Decimal(it["price"]) * 100)
            qty = int(it["qty"])
            line_reqs.append({
                "sku_id": it["sku"].id,
                "product": it["product"],
                "sku": it["sku"],
                "qty": qty,
                "price_cents": price_cents,
                "line_total_cents": price_cents * qty,
            })
            total_cents += price_cents * qty

        try:
            with transaction.atomic():
                # Lock SKUs to avoid race conditions
                sku_ids = [r["sku_id"] for r in line_reqs]
                locked_skus = (
                    SKU.objects
                    .select_for_update()
                    .select_related("product")
                    .filter(id__in=sku_ids, is_active=True)
                )
                locked_map = {s.id: s for s in locked_skus}

                # Validate availability
                for r in line_reqs:
                    s = locked_map.get(r["sku_id"])
                    if not s:
                        raise ValueError(f"SKU {r['sku_id']} not found or inactive.")
                    if not s.can_fulfill(r["qty"]):
                        raise ValueError(f"Not enough stock for {s.code}. Available: {s.stock_available}")

                # Create order
                order = Order.objects.create(
                    customer_name=name,
                    email=email,
                    address_line=address,
                    city=city,
                    state=state,
                    postal_code=postal,
                    total_cents=total_cents,
                )

                # Create items + deduct stock
                for r in line_reqs:
                    s = locked_map[r["sku_id"]]
                    OrderItem.objects.create(
                        order=order,
                        product=r["product"],
                        sku=s,
                        quantity=r["qty"],
                        price_cents=r["price_cents"],
                        line_total_cents=r["line_total_cents"],
                    )
                    s.deduct(r["qty"])

        except ValueError as e:
            messages.error(request, str(e))
            return render(request, "store/checkout.html", {"cart": cart})
        except Exception:
            messages.error(request, "Unexpected error placing order. Please try again.")
            return render(request, "store/checkout.html", {"cart": cart})

        cart.clear()
        return render(request, "store/order_thanks.html", {"order": order})

    # GET
    return render(request, "store/checkout.html", {"cart": Cart(request)})
