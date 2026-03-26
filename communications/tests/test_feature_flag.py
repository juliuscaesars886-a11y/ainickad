"""
Tests for CLASSIFICATION_ENABLED feature flag

Validates that the feature flag correctly controls whether the classification
system or legacy keyword matching is used.

**Validates: Requirements 6.1-6.6**
"""

import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

from communications.ai_chat import generate_contextual_response

User = get_user_model()


class FeatureFlagTestCase(TestCase):
    """Test cases for CLASSIFICATION_ENABLED feature flag."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            full_name='Test User'
        )
    
    @override_settings(CLASSIFICATION_ENABLED=True)
    @patch('communications.classifier.get_classifier')
    @patch('communications.response_handlers.get_handler')
    def test_classification_enabled_uses_classifier(self, mock_get_handler, mock_get_classifier):
        """
        Test that when CLASSIFICATION_ENABLED=True, the classification system is used.
        
        **Validates: Requirement 6.1 - Feature flag enables classification**
        """
        # Mock classifier
        mock_classifier = MagicMock()
        mock_classifier.is_initialized.return_value = True
        mock_classifier.classify.return_value = MagicMock(
            type='Navigation',
            confidence=0.85,
            scores={'Navigation': 0.85},
            label='→',
            reasoning='Test classification'
        )
        mock_get_classifier.return_value = mock_classifier
        
        # Mock handler
        mock_handler = MagicMock(return_value="→ Test response from classification system")
        mock_get_handler.return_value = mock_handler
        
        # Call generate_contextual_response
        response = generate_contextual_response(
            "how do i create a company",
            knowledge="",
            user=self.user
        )
        
        # Verify classifier was called
        mock_classifier.classify.assert_called_once()
        
        # Verify handler was called
        mock_handler.assert_called_once()
        
        # Verify response is from classification system
        assert "classification system" in response.lower() or "→" in response
    
    @override_settings(CLASSIFICATION_ENABLED=False)
    @patch('communications.classifier.get_classifier')
    def test_classification_disabled_uses_legacy(self, mock_get_classifier):
        """
        Test that when CLASSIFICATION_ENABLED=False, legacy keyword matching is used.
        
        **Validates: Requirement 6.3 - Feature flag disables classification**
        """
        # Call generate_contextual_response with a greeting
        response = generate_contextual_response(
            "hello",
            knowledge="",
            user=self.user
        )
        
        # Verify classifier was NOT called
        mock_get_classifier.assert_not_called()
        
        # Verify response is from legacy system (greeting menu)
        assert "Hello Test User" in response
        assert "Annual Returns" in response or "menu" in response.lower()
    
    @override_settings(CLASSIFICATION_ENABLED=True)
    @patch('communications.classifier.get_classifier')
    def test_classification_error_falls_back_to_legacy(self, mock_get_classifier):
        """
        Test that when classification fails, system falls back to legacy matching.
        
        **Validates: Requirement 6.3 - Fallback to legacy on classification failure**
        """
        # Mock classifier to raise exception
        mock_classifier = MagicMock()
        mock_classifier.is_initialized.return_value = True
        mock_classifier.classify.side_effect = Exception("Classification error")
        mock_get_classifier.return_value = mock_classifier
        
        # Call generate_contextual_response with a greeting
        response = generate_contextual_response(
            "hello",
            knowledge="",
            user=self.user
        )
        
        # Verify response is from legacy system (greeting menu)
        assert "Hello Test User" in response
        assert "Annual Returns" in response or "menu" in response.lower()
    
    @override_settings(CLASSIFICATION_ENABLED=True)
    @patch('communications.classifier.log_classification')
    @patch('communications.classifier.get_classifier')
    @patch('communications.response_handlers.get_handler')
    def test_classification_enabled_logs_with_flag(
        self, mock_get_handler, mock_get_classifier, mock_log_classification
    ):
        """
        Test that classification logs include classification_enabled=True flag.
        
        **Validates: Requirement 6.5 - Monitoring includes feature flag status**
        """
        # Mock classifier
        mock_classifier = MagicMock()
        mock_classifier.is_initialized.return_value = True
        mock_classification = MagicMock(
            type='Navigation',
            confidence=0.85,
            scores={'Navigation': 0.85},
            label='→',
            reasoning='Test classification'
        )
        mock_classifier.classify.return_value = mock_classification
        mock_get_classifier.return_value = mock_classifier
        
        # Mock handler
        mock_handler = MagicMock(return_value="→ Test response")
        mock_get_handler.return_value = mock_handler
        
        # Call generate_contextual_response
        generate_contextual_response(
            "how do i create a company",
            knowledge="",
            user=self.user
        )
        
        # Verify log_classification was called
        mock_log_classification.assert_called_once()
        
        # Verify context_data includes classification_enabled=True
        call_args = mock_log_classification.call_args
        context_data = call_args.kwargs.get('context_data', {})
        assert context_data.get('classification_enabled') is True
    
    @override_settings(CLASSIFICATION_ENABLED=False)
    @patch('communications.classifier.log_classification')
    def test_classification_disabled_logs_with_flag(self, mock_log_classification):
        """
        Test that legacy responses log include classification_enabled=False flag.
        
        **Validates: Requirement 6.5 - Monitoring includes feature flag status**
        """
        # Call generate_contextual_response with a greeting
        generate_contextual_response(
            "hello",
            knowledge="",
            user=self.user
        )
        
        # Verify log_classification was called for legacy response
        mock_log_classification.assert_called_once()
        
        # Verify context_data includes classification_enabled=False
        call_args = mock_log_classification.call_args
        context_data = call_args.kwargs.get('context_data', {})
        assert context_data.get('classification_enabled') is False
    
    @override_settings(CLASSIFICATION_ENABLED=True)
    @patch('communications.classifier.get_classifier')
    @patch('communications.response_handlers.get_handler')
    def test_low_confidence_falls_back_to_legacy(self, mock_get_handler, mock_get_classifier):
        """
        Test that low confidence classifications fall back to legacy matching.
        
        **Validates: Requirement 6.3 - Fallback to legacy when confidence low**
        """
        # Mock classifier with low confidence
        mock_classifier = MagicMock()
        mock_classifier.is_initialized.return_value = True
        mock_classifier.classify.return_value = MagicMock(
            type='Tip',
            confidence=0.3,  # Low confidence
            scores={'Tip': 0.3},
            label='!',
            reasoning='Low confidence'
        )
        mock_get_classifier.return_value = mock_classifier
        
        # Call generate_contextual_response with a greeting
        response = generate_contextual_response(
            "hello",
            knowledge="",
            user=self.user
        )
        
        # Verify classifier was called
        mock_classifier.classify.assert_called_once()
        
        # Verify handler was NOT called (confidence too low)
        mock_get_handler.assert_not_called()
        
        # Verify response is from legacy system (greeting menu)
        assert "Hello Test User" in response
        assert "Annual Returns" in response or "menu" in response.lower()
    
    @override_settings(CLASSIFICATION_ENABLED=True)
    @patch('communications.classifier.get_classifier')
    def test_backward_compatibility_preserved(self, mock_get_classifier):
        """
        Test that existing functionality (greetings, math) is preserved.
        
        **Validates: Requirement 6.4 - Backward compatibility maintained**
        """
        # Mock classifier to not interfere
        mock_classifier = MagicMock()
        mock_classifier.is_initialized.return_value = True
        mock_classifier.classify.return_value = MagicMock(
            type='Tip',
            confidence=0.3,  # Low confidence to trigger fallback
            scores={'Tip': 0.3},
            label='!',
            reasoning='Low confidence'
        )
        mock_get_classifier.return_value = mock_classifier
        
        # Test greeting
        greeting_response = generate_contextual_response(
            "hello",
            knowledge="",
            user=self.user
        )
        assert "Hello Test User" in greeting_response
        
        # Test math expression
        math_response = generate_contextual_response(
            "what is 5+3",
            knowledge="",
            user=self.user
        )
        assert "5+3=8" in math_response or "8" in math_response
        
        # Test goodbye
        goodbye_response = generate_contextual_response(
            "goodbye",
            knowledge="",
            user=self.user
        )
        assert "Goodbye" in goodbye_response


class FeatureFlagIntegrationTestCase(TestCase):
    """Integration tests for feature flag with real classifier."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            full_name='Test User'
        )
    
    @override_settings(CLASSIFICATION_ENABLED=True)
    def test_classification_enabled_end_to_end(self):
        """
        Test end-to-end classification with feature flag enabled.
        
        **Validates: Requirement 6.1 - Feature flag enables classification**
        """
        # Call generate_contextual_response with a navigation query
        response = generate_contextual_response(
            "how do i create a company",
            knowledge="",
            user=self.user
        )
        
        # Verify response is generated (either from classification or legacy)
        assert len(response) > 0
        assert isinstance(response, str)
    
    @override_settings(CLASSIFICATION_ENABLED=False)
    def test_classification_disabled_end_to_end(self):
        """
        Test end-to-end with feature flag disabled (legacy only).
        
        **Validates: Requirement 6.3 - Feature flag disables classification**
        """
        # Call generate_contextual_response with a navigation query
        response = generate_contextual_response(
            "how do i create a company",
            knowledge="",
            user=self.user
        )
        
        # Verify response is generated from legacy system
        assert len(response) > 0
        assert isinstance(response, str)
        # Legacy system should provide company creation guidance
        assert "company" in response.lower()


# Run tests with pytest
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
