from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Category, Product
User = get_user_model()
class CatalogTests(TestCase):
    def test_product_creation(self):
        user = User.objects.create_user(username="x", password="StrongPass123!")
        category = Category.objects.create(name="Grains")
        product = Product.objects.create(name="Rice", sku="RICE-001", category=category, quantity=10)
        self.assertEqual(product.quantity, 10)
