from django import template

register = template.Library()

@register.filter
def filter_product(products, product_id):
    try:
        return products.get(id=int(product_id))
    except (ValueError, products.model.DoesNotExist):
        return None