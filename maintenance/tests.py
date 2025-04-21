from django.test import TestCase
from .models import MaintenanceCategory

class MaintenanceCategoryTests(TestCase):
    def setUp(self):
        # Create a test category
        MaintenanceCategory.objects.create(name="Test Category", description="Test Description")

    def test_category_creation(self):
        """Test that a category can be created and retrieved"""
        category = MaintenanceCategory.objects.get(name="Test Category")
        self.assertEqual(category.description, "Test Description")
        self.assertEqual(str(category), "Test Category")
