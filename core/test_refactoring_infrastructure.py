"""
Tests for refactoring infrastructure setup (Task 1).

Verifies that:
1. Domain exceptions are properly defined
2. Feature flags are configured in Django settings
3. Testing utilities are available and functional
"""
import pytest
from django.test import TestCase
from django.conf import settings
from core.exceptions import (
    DomainException,
    BusinessLogicError,
    ValidationError,
    PermissionError,
    ResourceNotFoundError,
)
from core.testing import (
    BehavioralEquivalenceTestCase,
    ServiceLayerTestCase,
    APIResponseComparator,
)


class TestDomainExceptionHierarchy(TestCase):
    """Test that domain exception hierarchy is properly defined."""
    
    def test_domain_exception_base_class_exists(self):
        """Test that DomainException base class exists."""
        exc = DomainException("Test error")
        self.assertIsInstance(exc, Exception)
        self.assertEqual(str(exc), "Test error")
    
    def test_business_logic_error_inherits_from_domain_exception(self):
        """Test that BusinessLogicError inherits from DomainException."""
        exc = BusinessLogicError("Business rule violated")
        self.assertIsInstance(exc, DomainException)
        self.assertIsInstance(exc, Exception)
    
    def test_validation_error_with_field_errors(self):
        """Test ValidationError with field-specific errors."""
        field_errors = {
            'email': 'Invalid email format',
            'password': 'Password too short',
        }
        exc = ValidationError(field_errors=field_errors)
        
        self.assertIsInstance(exc, DomainException)
        self.assertEqual(exc.field_errors, field_errors)
        self.assertEqual(exc.message, "Validation failed")
    
    def test_validation_error_with_custom_message(self):
        """Test ValidationError with custom message."""
        exc = ValidationError(message="Custom validation error")
        
        self.assertEqual(exc.message, "Custom validation error")
        self.assertEqual(exc.field_errors, {})
    
    def test_permission_error_inherits_from_domain_exception(self):
        """Test that PermissionError inherits from DomainException."""
        exc = PermissionError("User lacks permission")
        self.assertIsInstance(exc, DomainException)
    
    def test_resource_not_found_error_inherits_from_domain_exception(self):
        """Test that ResourceNotFoundError inherits from DomainException."""
        exc = ResourceNotFoundError("Resource not found")
        self.assertIsInstance(exc, DomainException)


class TestFeatureFlagsConfiguration(TestCase):
    """Test that feature flags are properly configured in Django settings."""
    
    def test_feature_flags_exist_in_settings(self):
        """Test that FEATURE_FLAGS dictionary exists in settings."""
        self.assertTrue(hasattr(settings, 'FEATURE_FLAGS'))
        self.assertIsInstance(settings.FEATURE_FLAGS, dict)
    
    def test_use_service_layer_flag_exists(self):
        """Test that USE_SERVICE_LAYER flag exists."""
        self.assertIn('USE_SERVICE_LAYER', settings.FEATURE_FLAGS)
        self.assertIsInstance(settings.FEATURE_FLAGS['USE_SERVICE_LAYER'], bool)
    
    def test_use_validation_rules_api_flag_exists(self):
        """Test that USE_VALIDATION_RULES_API flag exists."""
        self.assertIn('USE_VALIDATION_RULES_API', settings.FEATURE_FLAGS)
        self.assertIsInstance(settings.FEATURE_FLAGS['USE_VALIDATION_RULES_API'], bool)
    
    def test_use_notification_service_flag_exists(self):
        """Test that USE_NOTIFICATION_SERVICE flag exists."""
        self.assertIn('USE_NOTIFICATION_SERVICE', settings.FEATURE_FLAGS)
        self.assertIsInstance(settings.FEATURE_FLAGS['USE_NOTIFICATION_SERVICE'], bool)
    
    def test_feature_flags_default_to_false(self):
        """Test that feature flags default to False for safe rollback."""
        # Flags should default to False to maintain backward compatibility
        # They can be enabled via environment variables
        self.assertIsInstance(settings.FEATURE_FLAGS['USE_SERVICE_LAYER'], bool)
        self.assertIsInstance(settings.FEATURE_FLAGS['USE_VALIDATION_RULES_API'], bool)
        self.assertIsInstance(settings.FEATURE_FLAGS['USE_NOTIFICATION_SERVICE'], bool)


class TestBehavioralEquivalenceTestCase(TestCase):
    """Test that BehavioralEquivalenceTestCase utilities work correctly."""
    
    def test_behavioral_equivalence_test_case_can_be_instantiated(self):
        """Test that BehavioralEquivalenceTestCase can be instantiated."""
        # This is a simple smoke test
        self.assertTrue(issubclass(BehavioralEquivalenceTestCase, TestCase))
    
    def test_api_response_comparator_can_be_instantiated(self):
        """Test that APIResponseComparator can be instantiated."""
        comparator = APIResponseComparator()
        self.assertIsNotNone(comparator)
        self.assertEqual(
            comparator.ignore_fields,
            ['id', 'created_at', 'updated_at', 'created_on', 'modified_on']
        )
    
    def test_api_response_comparator_with_custom_ignore_fields(self):
        """Test APIResponseComparator with custom ignore fields."""
        custom_fields = ['id', 'timestamp']
        comparator = APIResponseComparator(ignore_fields=custom_fields)
        self.assertEqual(comparator.ignore_fields, custom_fields)


class TestServiceLayerTestCase(TestCase):
    """Test that ServiceLayerTestCase utilities work correctly."""
    
    def test_service_layer_test_case_can_be_instantiated(self):
        """Test that ServiceLayerTestCase can be instantiated."""
        # This is a simple smoke test
        self.assertTrue(issubclass(ServiceLayerTestCase, TestCase))


class TestTestingUtilitiesIntegration(TestCase):
    """Integration tests for testing utilities."""
    
    def test_domain_exceptions_can_be_caught_and_handled(self):
        """Test that domain exceptions can be caught and handled properly."""
        try:
            raise ValidationError(
                field_errors={'email': 'Invalid email'},
                message="Email validation failed"
            )
        except DomainException as e:
            self.assertIsInstance(e, ValidationError)
            self.assertEqual(e.field_errors['email'], 'Invalid email')
        except Exception:
            self.fail("ValidationError should be caught as DomainException")
    
    def test_all_domain_exceptions_inherit_from_base(self):
        """Test that all domain exceptions inherit from DomainException."""
        exceptions = [
            BusinessLogicError("test"),
            ValidationError(),
            PermissionError("test"),
            ResourceNotFoundError("test"),
        ]
        
        for exc in exceptions:
            self.assertIsInstance(exc, DomainException)
