from django.test import TestCase
from django.contrib.auth import get_user_model
from catalog.models import Category, Product
from .services import apply_stock_counts, record_consumption
from .models import StockMovement
User = get_user_model()
class InventoryServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="manager", password="StrongPass123!")
        self.category = Category.objects.create(name="Staples")
        self.product = Product.objects.create(name="Rice", sku="R-1", category=self.category, quantity=20)
    def test_batch_count_creates_movement(self):
        batch, changed = apply_stock_counts({self.product.pk: 15}, self.user, "Count")
        self.product.refresh_from_db()
        self.assertEqual(changed, 1)
        self.assertEqual(self.product.quantity, 15)
        self.assertEqual(StockMovement.objects.filter(batch=batch).count(), 1)
    def test_consumption_updates_last_used(self):
        record_consumption(self.product.pk, 2, self.user, "Kitchen use")
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 18)
        self.assertIsNotNone(self.product.last_used_at)
    def test_batch_rejects_negative(self):
        with self.assertRaises(ValueError):
            apply_stock_counts({self.product.pk: -1}, self.user)
