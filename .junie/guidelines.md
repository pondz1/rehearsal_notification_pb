# Development Guidelines for Rehearsal Notification Project

This document provides essential information for developers working on the Rehearsal Notification project.

## Build/Configuration Instructions

### Environment Setup

1. **Python Environment**:
   - This project requires Python 3.8+ 
   - Create a virtual environment:
     ```
     python -m venv .venv
     ```
   - Activate the virtual environment:
     - Windows: `.venv\Scripts\activate`
     - Linux/Mac: `source .venv/bin/activate`

2. **Dependencies**:
   - Install required packages:
     ```
     pip install -r requirements.txt
     ```

3. **Database Configuration**:
   - The project uses SQLite by default (configured in `core/settings.py`)
   - Run migrations to set up the database:
     ```
     python manage.py migrate
     ```

4. **Email Configuration**:
   - Update the email settings in `core/settings.py` with your SMTP credentials:
     ```python
     EMAIL_HOST_USER = 'your-email@gmail.com'
     EMAIL_HOST_PASSWORD = 'your-app-specific-password'
     DEFAULT_FROM_EMAIL = 'Maintenance System <your-email@gmail.com>'
     ```

5. **Running the Development Server**:
   ```
   python manage.py runserver
   ```

6. **Creating a Superuser**:
   ```
   python manage.py createsuperuser
   ```

## Testing Information

### Running Tests

1. **Run All Tests**:
   ```
   python manage.py test
   ```

2. **Run Tests for a Specific App**:
   ```
   python manage.py test maintenance
   ```

3. **Run a Specific Test Class**:
   ```
   python manage.py test maintenance.tests.MaintenanceCategoryTests
   ```

4. **Run a Specific Test Method**:
   ```
   python manage.py test maintenance.tests.MaintenanceCategoryTests.test_category_creation
   ```

### Creating New Tests

1. **Test Structure**:
   - Tests should be placed in the `tests.py` file within each app
   - For complex apps, consider creating a `tests` directory with multiple test files

2. **Test Naming Conventions**:
   - Test classes should be named with the format `{ModelName}Tests`
   - Test methods should start with `test_` and have descriptive names

3. **Example Test**:
   ```python
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
   ```

4. **Test Database**:
   - Django automatically creates a test database for running tests
   - The test database is destroyed after tests are completed

## Additional Development Information

### Project Structure

- **Core App**: Contains project-wide settings and configurations
- **Maintenance App**: Main application with models for maintenance requests, assignments, etc.
- **Templates**: HTML templates organized by app and functionality
- **Media**: Stores uploaded files (images, etc.)

### Code Style Guidelines

1. **PEP 8**:
   - Follow PEP 8 style guide for Python code
   - Use 4 spaces for indentation
   - Maximum line length of 120 characters

2. **Django Best Practices**:
   - Use Django's ORM for database operations
   - Implement proper form validation
   - Use Django's built-in security features

3. **Model Design**:
   - Define `__str__` methods for all models
   - Use appropriate field types
   - Define Meta classes for ordering and permissions

### Permissions System

The project uses a custom permissions system defined in `settings.py`:

```python
MAINTENANCE_PERMISSIONS = {
    'can_manage_maintenance': 'maintenance.can_manage_maintenance',
    'can_assign_technician': 'maintenance.can_assign_technician',
    'can_update_status': 'maintenance.can_update_status',
    'can_view_reports': 'maintenance.can_view_reports',
}
```

### Notification System

The project includes a notification system with multiple channels:

```python
NOTIFICATION_CHANNELS = {
    'email': True,
    'line': True,
    'in_app': True
}
```

### Internationalization

The project is configured for Thai language and Bangkok timezone:

```python
LANGUAGE_CODE = 'th-TH'
TIME_ZONE = 'Asia/Bangkok'
```

### Frontend Framework

The project uses Tailwind CSS via crispy-tailwind for styling forms and UI components.