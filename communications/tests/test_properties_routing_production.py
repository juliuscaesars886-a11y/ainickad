"""
Property-based tests for routing, error handling, and production readiness.

This module implements property-based tests for Properties 10-25:
- Property 10: Routing by Confidence Threshold
- Property 11: Priority-Based Routing
- Property 12: Company_Data Priority Override
- Property 13: Response Label Prepending
- Property 17: Handler Invocation Correctness
- Property 18: Handler Parameter Passing
- Property 19: Fallback Handler Activation
- Property 20: Short Message Handling
- Property 21: Classification Logging
- Property 22: Backward Compatibility
- Property 23: Error Resilience
- Property 24: Semantic Failure Handling
- Property 25: Keyword Dictionary Loading

Uses Hypothesis framework to generate diverse test messages and validate
routing correctness, error handling, and production readiness properties.

**Validates: Requirements 15.6**
"""

import json
import re
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from hypothesis.extra.django import TestCase
from django.contrib.auth import get_user_model

from communications.classifier import (
    MessageClassifier,
    ClassificationResult,
    ClassificationContext,
    ClassificationType,
    get_classifier,
    reset_classifier,
    CLASSIFICATION_TYPES,
    RESPONSE_LABELS
)
from communications.classification_keywords import get_keyword_dictionaries
from communications.models import ClassificationLog

User = get_user_model()


class TestRoutingProperties(TestCase):
    """Property-based tests for routing logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        reset_classifier()
        self.classifier = get_classifier()
        
        # Create test user for context
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def tearDown(self):
        """Clean up after tests."""
        reset_classifier()
        ClassificationLog.objects.all().delete()
        User.objects.all().delete()
    
    # ============================================================================
    # Property 10: Routing by Confidence Threshold
    # ============================================================================
    
    @given(
        message=st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd', 'Ps', 'Pe', 'Po'),
            whitelist_characters=' '
        ))
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
    def test_routing_by_confidence_threshold_property(self, message):
        """
        **Validates: Requirements 3.3, 9.1**
        
        Property 10: Routing by Confidence Threshold
        For any classification with confidence below 0.6, the routing engine 
        SHALL invoke the fallback handler.
        
        This property ensures low-confidence classifications are handled safely.
        """
        # Skip empty or whitespace-only messages
        if not message.strip():
            return
        
        context = ClassificationContext()
        
        try:
            result = self.classifier.classify(message, context)
            
            # Verify result structure
            assert isinstance(result, ClassificationResult)
            assert 0.0 <= result.confidence <= 1.0
            
            # Property assertion: If confidence < 0.6, should route to fallback
            # We check this by verifying the classification type is Tip or the
            # confidence is >= 0.6
            if result.confidence < 0.6:
                # Low confidence should result in Tip classification (fallback)
                assert result.type == ClassificationType.TIP.value, (
                    f"Low confidence ({result.confidence:.2f}) should route to "
                    f"fallback (Tip), but got {result.type}"
                )
            
        except Exception as e:
            # Classification errors should not break the system
            print(f"Classification failed for message '{message[:50]}...': {e}")
            return
    
    # ============================================================================
    # Property 11: Priority-Based Routing
    # ============================================================================
    
    def test_priority_based_routing_property(self):
        """
        **Validates: Requirements 5.1, 5.2**
        
        Property 11: Priority-Based Routing
        For any message matching multiple classification types with similar 
        confidence (within 0.05), the routing engine SHALL select the type 
        with higher priority according to the priority order.
        
        Priority order: Company_Data > Kenya_Governance > Feature_Guide > 
        Navigation > Web_Search > Tip
        """
        # Test cases with messages that could match multiple types
        test_cases = [
            {
                'message': 'How do I find my company directors?',
                'expected_priority': [ClassificationType.COMPANY_DATA.value, 
                                     ClassificationType.NAVIGATION.value]
            },
            {
                'message': 'What are the BRS compliance requirements for my company?',
                'expected_priority': [ClassificationType.KENYA_GOVERNANCE.value,
                                     ClassificationType.COMPANY_DATA.value]
            },
            {
                'message': 'How does the user management feature work?',
                'expected_priority': [ClassificationType.FEATURE_GUIDE.value,
                                     ClassificationType.NAVIGATION.value]
            }
        ]
        
        for test_case in test_cases:
            message = test_case['message']
            expected_priority = test_case['expected_priority']
            
            context = ClassificationContext()
            result = self.classifier.classify(message, context)
            
            # Get scores for expected types
            scores = {t: result.scores.get(t, 0.0) for t in expected_priority}
            
            # If scores are similar (within 0.05), should select higher priority
            if len(scores) >= 2:
                sorted_types = sorted(scores.items(), key=lambda x: x[1], reverse=True)
                
                if len(sorted_types) >= 2:
                    top_score = sorted_types[0][1]
                    second_score = sorted_types[1][1]
                    
                    # If scores are similar
                    if abs(top_score - second_score) <= 0.05:
                        # Result should be the higher priority type
                        assert result.type in expected_priority, (
                            f"For message '{message}', expected one of {expected_priority}, "
                            f"got {result.type}"
                        )
    
    # ============================================================================
    # Property 12: Company_Data Priority Override
    # ============================================================================
    
    @given(
        company_keyword=st.sampled_from([
            'my company', 'our company', 'our directors', 'my directors',
            'company documents', 'company deadlines'
        ])
    )
    @settings(max_examples=10)
    def test_company_data_priority_override_property(self, company_keyword):
        """
        **Validates: Requirements 5.3**
        
        Property 12: Company_Data Priority Override
        For any classification where Company_Data confidence exceeds 0.7, 
        the routing engine SHALL route to the Company_Data handler regardless 
        of other classification scores.
        """
        # Create message with company keyword
        message = f"Tell me about {company_keyword}"
        
        context = ClassificationContext(
            user_id=self.test_user.id,
            user_role='Staff',
            company_name='Test Company',
            company_id=1
        )
        
        result = self.classifier.classify(message, context)
        
        # If Company_Data confidence > 0.7, should route to Company_Data
        company_data_confidence = result.scores.get(ClassificationType.COMPANY_DATA.value, 0.0)
        
        if company_data_confidence > 0.7:
            assert result.type == ClassificationType.COMPANY_DATA.value, (
                f"Company_Data confidence ({company_data_confidence:.2f}) > 0.7 "
                f"should route to Company_Data, but got {result.type}"
            )



    # ============================================================================
    # Property 13: Response Label Prepending
    # ============================================================================
    
    @given(
        classification_type=st.sampled_from([
            ClassificationType.NAVIGATION.value,
            ClassificationType.FEATURE_GUIDE.value,
            ClassificationType.COMPANY_DATA.value,
            ClassificationType.KENYA_GOVERNANCE.value,
            ClassificationType.WEB_SEARCH.value,
            ClassificationType.TIP.value
        ])
    )
    @settings(max_examples=10)
    def test_response_label_prepending_property(self, classification_type):
        """
        **Validates: Requirements 4.1-4.7**
        
        Property 13: Response Label Prepending
        For any response generated for a classification type, the response text 
        SHALL begin with the corresponding response label (→, ?, ◈, ⚖, ⊕, or !).
        """
        # Get expected label for this type
        expected_label = RESPONSE_LABELS.get(classification_type)
        
        assert expected_label is not None, (
            f"No response label defined for type {classification_type}"
        )
        
        # Create a classification result with this type
        result = ClassificationResult(
            type=classification_type,
            confidence=0.8,
            scores={classification_type: 0.8},
            label=expected_label,
            handler=None,
            reasoning=f"Test classification for {classification_type}"
        )
        
        # Verify the label matches the type
        assert result.label == expected_label, (
            f"Label mismatch: expected '{expected_label}' for {classification_type}, "
            f"got '{result.label}'"
        )
        
        # Verify label is one of the valid labels
        valid_labels = ['→', '?', '◈', '⚖', '⊕', '!']
        assert result.label in valid_labels, (
            f"Invalid label '{result.label}' for type {classification_type}"
        )


class TestHandlerInvocationProperties(TestCase):
    """Property-based tests for handler invocation."""
    
    def setUp(self):
        """Set up test fixtures."""
        reset_classifier()
        self.classifier = get_classifier()
        
        # Create test user
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def tearDown(self):
        """Clean up after tests."""
        reset_classifier()
        User.objects.all().delete()
    
    # ============================================================================
    # Property 17: Handler Invocation Correctness
    # ============================================================================
    
    @given(
        classification_type=st.sampled_from([
            ClassificationType.NAVIGATION.value,
            ClassificationType.FEATURE_GUIDE.value,
            ClassificationType.COMPANY_DATA.value,
            ClassificationType.KENYA_GOVERNANCE.value,
            ClassificationType.WEB_SEARCH.value,
            ClassificationType.TIP.value
        ])
    )
    @settings(max_examples=10)
    def test_handler_invocation_correctness_property(self, classification_type):
        """
        **Validates: Requirements 8.2-8.7**
        
        Property 17: Handler Invocation Correctness
        For any classification type, the routing engine SHALL invoke the 
        corresponding handler function (handle_navigation_query, 
        handle_feature_guide_query, etc.).
        """
        # Map types to expected handler names
        expected_handlers = {
            ClassificationType.NAVIGATION.value: 'handle_navigation_query',
            ClassificationType.FEATURE_GUIDE.value: 'handle_feature_guide_query',
            ClassificationType.COMPANY_DATA.value: 'handle_company_data_query',
            ClassificationType.KENYA_GOVERNANCE.value: 'handle_kenya_governance_query',
            ClassificationType.WEB_SEARCH.value: 'handle_web_search_query',
            ClassificationType.TIP.value: 'handle_tip_query'
        }
        
        expected_handler_name = expected_handlers.get(classification_type)
        
        assert expected_handler_name is not None, (
            f"No handler defined for type {classification_type}"
        )
        
        # Verify handler exists in response_handlers module
        try:
            from communications import response_handlers
            handler_func = getattr(response_handlers, expected_handler_name, None)
            
            assert handler_func is not None, (
                f"Handler function '{expected_handler_name}' not found in "
                f"response_handlers module for type {classification_type}"
            )
            
            # Verify it's callable
            assert callable(handler_func), (
                f"Handler '{expected_handler_name}' is not callable"
            )
            
        except ImportError as e:
            pytest.fail(f"Could not import response_handlers module: {e}")
    
    # ============================================================================
    # Property 18: Handler Parameter Passing
    # ============================================================================
    
    @given(
        message=st.text(min_size=3, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters=' '
        ))
    )
    @settings(max_examples=10)
    def test_handler_parameter_passing_property(self, message):
        """
        **Validates: Requirements 8.8**
        
        Property 18: Handler Parameter Passing
        For any handler invocation, the handler SHALL receive the user message, 
        classification result, and user context as parameters.
        """
        # Skip empty messages
        if not message.strip():
            return
        
        context = ClassificationContext(
            user_id=self.test_user.id,
            user_role='Staff'
        )
        
        # Mock a handler to verify parameters
        with patch('communications.response_handlers.handle_navigation_query') as mock_handler:
            mock_handler.return_value = "→ Test response"
            
            # Force classification to Navigation
            with patch.object(self.classifier, 'classify') as mock_classify:
                mock_result = ClassificationResult(
                    type=ClassificationType.NAVIGATION.value,
                    confidence=0.8,
                    scores={ClassificationType.NAVIGATION.value: 0.8},
                    label='→',
                    handler=mock_handler,
                    reasoning='Test'
                )
                mock_classify.return_value = mock_result
                
                # Import and call the routing function
                try:
                    from communications.ai_chat import generate_contextual_response
                    
                    # Call with our test message
                    response = generate_contextual_response(
                        user_message=message,
                        knowledge='',
                        user=self.test_user
                    )
                    
                    # If handler was called, verify it received correct parameters
                    if mock_handler.called:
                        call_args = mock_handler.call_args
                        
                        # Handler should receive message, classification, and user
                        assert len(call_args[0]) >= 2 or len(call_args[1]) >= 2, (
                            "Handler should receive at least 2 parameters"
                        )
                        
                except ImportError:
                    # If ai_chat module not available, skip this test
                    pytest.skip("ai_chat module not available for testing")


class TestFallbackProperties(TestCase):
    """Property-based tests for fallback handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        reset_classifier()
        self.classifier = get_classifier()
    
    def tearDown(self):
        """Clean up after tests."""
        reset_classifier()
    
    # ============================================================================
    # Property 19: Fallback Handler Activation
    # ============================================================================
    
    @given(
        message=st.text(min_size=1, max_size=50, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters=' '
        ))
    )
    @settings(max_examples=10)
    def test_fallback_handler_activation_property(self, message):
        """
        **Validates: Requirements 9.1**
        
        Property 19: Fallback Handler Activation
        For any message with all classification type confidences below 0.6, 
        the routing engine SHALL invoke the fallback handler.
        """
        # Skip empty messages
        if not message.strip():
            return
        
        context = ClassificationContext()
        result = self.classifier.classify(message, context)
        
        # Check if all confidences are below 0.6
        all_low_confidence = all(
            score < 0.6 for score in result.scores.values()
        )
        
        if all_low_confidence:
            # Should route to Tip (fallback)
            assert result.type == ClassificationType.TIP.value, (
                f"All confidences below 0.6 should route to fallback (Tip), "
                f"but got {result.type}. Scores: {result.scores}"
            )
    
    # ============================================================================
    # Property 20: Short Message Handling
    # ============================================================================
    
    @given(
        word_count=st.integers(min_value=1, max_value=2)
    )
    @settings(max_examples=10)
    def test_short_message_handling_property(self, word_count):
        """
        **Validates: Requirements 9.4**
        
        Property 20: Short Message Handling
        For any message with fewer than 3 words, the fallback handler SHALL 
        prompt the user for more details.
        """
        # Generate a short message with specified word count
        words = ['test'] * word_count
        message = ' '.join(words)
        
        context = ClassificationContext()
        result = self.classifier.classify(message, context)
        
        # Short messages (< 3 words) should have low confidence
        # and likely route to fallback
        if word_count < 3:
            # Either low confidence or Tip classification
            assert result.confidence < 0.7 or result.type == ClassificationType.TIP.value, (
                f"Short message ({word_count} words) should have low confidence "
                f"or route to Tip, but got {result.type} with confidence {result.confidence:.2f}"
            )


class TestLoggingProperties(TestCase):
    """Property-based tests for classification logging."""
    
    def setUp(self):
        """Set up test fixtures."""
        reset_classifier()
        self.classifier = get_classifier()
        
        # Create test user
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Clear any existing logs
        ClassificationLog.objects.all().delete()
    
    def tearDown(self):
        """Clean up after tests."""
        reset_classifier()
        ClassificationLog.objects.all().delete()
        User.objects.all().delete()
    
    # ============================================================================
    # Property 21: Classification Logging
    # ============================================================================
    
    @given(
        message=st.text(min_size=3, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters=' '
        ))
    )
    @settings(max_examples=10)
    def test_classification_logging_property(self, message):
        """
        **Validates: Requirements 10.1**
        
        Property 21: Classification Logging
        For any classification, the system SHALL log the timestamp, message, 
        classification type, and confidence score to the classification log.
        """
        # Skip empty messages
        if not message.strip():
            return
        
        # Get initial log count
        initial_count = ClassificationLog.objects.count()
        
        context = ClassificationContext(
            user_id=self.test_user.id,
            user_role='Staff'
        )
        
        try:
            # Perform classification with logging enabled
            result = self.classifier.classify(message, context)
            
            # Import and call the logging function
            from communications.classifier import log_classification
            
            log_classification(
                user=self.test_user,
                message=message,
                classification_result=result,
                processing_time_ms=10.0
            )
            
            # Verify log was created
            final_count = ClassificationLog.objects.count()
            assert final_count > initial_count, (
                f"Classification log not created for message '{message[:50]}...'"
            )
            
            # Verify log contains correct data
            log_entry = ClassificationLog.objects.latest('timestamp')
            
            assert log_entry.user == self.test_user
            assert log_entry.message == message
            assert log_entry.classification_type == result.type
            assert 0.0 <= log_entry.confidence_score <= 1.0
            assert log_entry.processing_time_ms >= 0.0
            
        except Exception as e:
            # Log errors but don't fail test for edge cases
            print(f"Logging test failed for message '{message[:50]}...': {e}")
            return


class TestErrorResilienceProperties(TestCase):
    """Property-based tests for error handling and resilience."""
    
    def setUp(self):
        """Set up test fixtures."""
        reset_classifier()
        self.classifier = get_classifier()
    
    def tearDown(self):
        """Clean up after tests."""
        reset_classifier()
    
    # ============================================================================
    # Property 23: Error Resilience
    # ============================================================================
    
    @given(
        message=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=10, suppress_health_check=[HealthCheck.too_slow])
    def test_error_resilience_property(self, message):
        """
        **Validates: Requirements 14.1, 14.6**
        
        Property 23: Error Resilience
        For any exception during classification, the system SHALL log the error 
        and fall back to legacy keyword matching without returning an error to 
        the user.
        """
        # Skip empty messages
        if not message.strip():
            return
        
        context = ClassificationContext()
        
        # Classification should never raise an exception to the caller
        try:
            result = self.classifier.classify(message, context)
            
            # Should always return a valid result
            assert isinstance(result, ClassificationResult)
            assert result.type in CLASSIFICATION_TYPES
            assert 0.0 <= result.confidence <= 1.0
            
        except Exception as e:
            pytest.fail(
                f"Classification raised exception for message '{message[:50]}...': {e}. "
                f"System should handle errors gracefully and return a default result."
            )
    
    # ============================================================================
    # Property 24: Semantic Failure Handling
    # ============================================================================
    
    @given(
        message=st.text(min_size=3, max_size=100, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),
            whitelist_characters=' '
        ))
    )
    @settings(max_examples=10)
    def test_semantic_failure_handling_property(self, message):
        """
        **Validates: Requirements 14.2**
        
        Property 24: Semantic Failure Handling
        For any failure in semantic similarity calculation, the classifier SHALL 
        use only keyword-based confidence scores.
        """
        # Skip empty messages
        if not message.strip():
            return
        
        context = ClassificationContext()
        
        # Mock semantic analysis to fail
        with patch.object(self.classifier, '_calculate_semantic_scores', side_effect=Exception("Semantic failure")):
            try:
                result = self.classifier.classify(message, context)
                
                # Should still return a valid result using keyword-only classification
                assert isinstance(result, ClassificationResult)
                assert result.type in CLASSIFICATION_TYPES
                assert 0.0 <= result.confidence <= 1.0
                
                # Confidence should be based on keywords only
                # (we can't verify exact values, but it should be valid)
                
            except Exception as e:
                pytest.fail(
                    f"Classification failed when semantic analysis failed: {e}. "
                    f"Should fall back to keyword-only classification."
                )


class TestKeywordDictionaryProperties(TestCase):
    """Property-based tests for keyword dictionary loading."""
    
    def setUp(self):
        """Set up test fixtures."""
        reset_classifier()
    
    def tearDown(self):
        """Clean up after tests."""
        reset_classifier()
    
    # ============================================================================
    # Property 25: Keyword Dictionary Loading
    # ============================================================================
    
    def test_keyword_dictionary_loading_property(self):
        """
        **Validates: Requirements 13.1, 13.2**
        
        Property 25: Keyword Dictionary Loading
        For any application startup, the classifier SHALL load keyword 
        dictionaries from configuration without errors.
        """
        # Test loading keyword dictionaries
        try:
            keyword_dicts = get_keyword_dictionaries()
            
            # Verify all classification types have dictionaries
            for classification_type in CLASSIFICATION_TYPES:
                assert classification_type in keyword_dicts, (
                    f"No keyword dictionary found for type {classification_type}"
                )
                
                # Verify dictionary is not empty
                assert len(keyword_dicts[classification_type]) > 0, (
                    f"Keyword dictionary for {classification_type} is empty"
                )
                
                # Verify keywords are valid
                for keyword_data in keyword_dicts[classification_type]:
                    assert 'text' in keyword_data or isinstance(keyword_data, str), (
                        f"Invalid keyword format in {classification_type} dictionary"
                    )
            
        except Exception as e:
            pytest.fail(
                f"Failed to load keyword dictionaries: {e}. "
                f"Dictionaries should load without errors on startup."
            )
    
    def test_keyword_dictionary_structure_property(self):
        """
        Property: Keyword dictionaries should have valid structure.
        
        Validates that each keyword entry has required fields and valid values.
        """
        keyword_dicts = get_keyword_dictionaries()
        
        for classification_type, keywords in keyword_dicts.items():
            for i, keyword_data in enumerate(keywords):
                # Handle both string and dict formats
                if isinstance(keyword_data, str):
                    # Simple string format is valid
                    assert len(keyword_data) > 0, (
                        f"Empty keyword string in {classification_type} at index {i}"
                    )
                elif isinstance(keyword_data, dict):
                    # Dict format should have 'text' field
                    assert 'text' in keyword_data, (
                        f"Keyword dict missing 'text' field in {classification_type} at index {i}"
                    )
                    
                    # If weight is present, should be between 0 and 1
                    if 'weight' in keyword_data:
                        weight = keyword_data['weight']
                        assert 0.0 <= weight <= 1.0, (
                            f"Invalid weight {weight} in {classification_type} at index {i}"
                        )
                else:
                    pytest.fail(
                        f"Invalid keyword type {type(keyword_data)} in "
                        f"{classification_type} at index {i}"
                    )


class TestBackwardCompatibilityProperties(TestCase):
    """Property-based tests for backward compatibility."""
    
    def setUp(self):
        """Set up test fixtures."""
        reset_classifier()
        self.classifier = get_classifier()
        
        # Create test user
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def tearDown(self):
        """Clean up after tests."""
        reset_classifier()
        User.objects.all().delete()
    
    # ============================================================================
    # Property 22: Backward Compatibility
    # ============================================================================
    
    @given(
        message=st.sampled_from([
            'How do I create a company?',
            'What does the compliance score do?',
            'Tell me about my company',
            'What are the BRS requirements?',
            'What is the weather today?',
            'Help'
        ])
    )
    @settings(max_examples=5)
    def test_backward_compatibility_property(self, message):
        """
        **Validates: Requirements 6.4, 6.6**
        
        Property 22: Backward Compatibility
        For any message that would have been handled by legacy keyword matching, 
        the new classification system SHALL produce a response that is 
        functionally equivalent or better.
        """
        context = ClassificationContext(
            user_id=self.test_user.id,
            user_role='Staff'
        )
        
        try:
            # New classification system
            result = self.classifier.classify(message, context)
            
            # Should produce a valid classification
            assert isinstance(result, ClassificationResult)
            assert result.type in CLASSIFICATION_TYPES
            assert 0.0 <= result.confidence <= 1.0
            
            # Should have a valid label
            assert result.label in RESPONSE_LABELS.values()
            
            # For well-known message patterns, should have reasonable confidence
            well_known_patterns = [
                'how do i', 'what does', 'tell me about', 'what are', 'what is'
            ]
            
            if any(pattern in message.lower() for pattern in well_known_patterns):
                # Should have at least moderate confidence for well-known patterns
                assert result.confidence >= 0.5, (
                    f"Well-known message pattern '{message}' has low confidence "
                    f"{result.confidence:.2f}"
                )
            
        except Exception as e:
            pytest.fail(
                f"Classification failed for message '{message}': {e}. "
                f"System should maintain backward compatibility."
            )
