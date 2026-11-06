from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import UserProfile
User = get_user_model()
class AccountsTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(username="manager@gmail.com", email="manager@gmail.com", password="StrongPass123!")
        UserProfile.objects.create(user=self.manager, role="MANAGER")
    def test_email_login(self):
        response = self.client.post(reverse("accounts:login"), {"email":"manager@gmail.com","password":"StrongPass123!"})
        self.assertEqual(response.status_code, 302)
    def test_manager_is_denied_user_admin(self):
        self.client.login(username="manager@gmail.com", password="StrongPass123!")
        self.assertEqual(self.client.get(reverse("accounts:user_list")).status_code, 403)
