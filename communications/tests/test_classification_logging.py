"""
Tests for classification logging and monitoring functionality.

Tests:
- Performance warning logging (> 500ms)
- Low confidence warning logging (< 0.6)
- Classification log creation
- Metrics calculation

**Validates: Requirements 10.1-10.6, 11.3**
"""

import logging
from django.test import TestCase
from django.contrib.auth import get_user_model
from communications.models import ClassificationLog
from communications.classifier import (
    ClassificationResult,
    ClassificationType,
    RESPONSE_LABELS,
    log_classification
)

User = get_user_model()


class ClassificationLoggingTestCase(TestCase):
    """Test classification logging functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            full_name='Test User'
        )
        
        # Capture log messages
        self.log_handler = logging.handlers.MemoryHandler(capacity=100)
        self.logger = logging.getLogger('communications.classifier')
        self.logger.addHandler(self.log_handler)
        self.logger.setLevel(logging.DEBUG)
    
    def tearDown(self):
        """Clean up after tests."""
        self.logger.removeHandler(self.log_handler)
    
    def test_log_classification_creates_database_entry(self):
        """Test that log_classification creates a database entry."""
        # Create classification result
        result = ClassificationResult(
            type=ClassificationType.NAVIGATION.value,
            confidence=0.85,
            scores={
                ClassificationType.NAVIGATION.value: 0.85,
                ClassificationType.FEATURE_GUIDE.value: 0.45,
                ClassificationType.COMPANY_DATA.value: 0.30,
                ClassificationType.KENYA_GOVERNANCE.value: 0.25,
                ClassificationType.WEB_SEARCH.value: 0.15,
                ClassificationType.TIP.value: 0.10,
            },
            label=RESPONSE_LABELS[ClassificationType.NAVIGATION.value]
        )
        
        # Log classification
        log_classification(
            classification_result=result,
            user_message="How do I create a company?",
            user=self.user,
            processing_time_ms=150.5,
            context_data={'user_role': 'Admin'}
        )
        
        # Verify database entry created
        self.assertEqual(ClassificationLog.objects.count(), 1)
        
        log_entry = ClassificationLog.objects.first()
        self.assertEqual(log_entry.user, self.user)
        self.assertEqual(log_entry.message, "How do I create a company?")
        self.assertEqual(log_entry.classification_type, ClassificationType.NAVIGATION.value)
        self.assertEqual(log_entry.confidence_score, 0.85)
        self.assertEqual(log_entry.processing_time_ms, 150)
        self.assertEqual(log_entry.context_data, {'user_role': 'Admin'})
        self.assertEqual(log_entry.user_feedback, 'none')
    
    def test_performance_warning_logged_for_slow_classification(self):
        """Test that performance warning is logged for classifications > 500ms."""
        # Create classification result
        result = ClassificationResult(
            type=ClassificationType.NAVIGATION.value,
            confidence=0.85,
            scores={t: 0.0 for t in [
                ClassificationType.NAVIGATION.value,
                ClassificationType.FEATURE_GUIDE.value,
                ClassificationType.COMPANY_DATA.value,
                ClassificationType.KENYA_GOVERNANCE.value,
                ClassificationType.WEB_SEARCH.value,
                ClassificationType.TIP.value,
            ]},
            label=RESPONSE_LABELS[ClassificationType.NAVIGATION.value]
        )
        result.scores[ClassificationType.NAVIGATION.value] = 0.85
        
        # Log classification with slow processing time
        log_classification(
            classification_result=result,
            user_message="How do I create a company?",
            user=self.user,
            processing_time_ms=523.4  # > 500ms
        )
        
        # Flush log handler
        self.log_handler.flush()
        
        # Check that warning was logged
        log_records = [record for record in self.logger.handlers[0].buffer]
        performance_warnings = [
            record for record in log_records
            if record.levelname == 'WARNING' and 'PERFORMANCE WARNING' in record.message
        ]
        
        self.assertGreater(len(performance_warnings), 0, "Performance warning should be logged")
        
        warning_message = performance_warnings[0].message
        self.assertIn('523.4ms', warning_message)
        self.assertIn('threshold: 500ms', warning_message)
        self.assertIn('How do I create a company?', warning_message)
    
    def test_no_performance_warning_for_fast_classification(self):
        """Test that no performance warning is logged for fast classifications."""
        # Create classification result
        result = ClassificationResult(
            type=ClassificationType.NAVIGATION.value,
            confidence=0.85,
            scores={t: 0.0 for t in [
                ClassificationType.NAVIGATION.value,
                ClassificationType.FEATURE_GUIDE.value,
                ClassificationType.COMPANY_DATA.value,
                ClassificationType.KENYA_GOVERNANCE.value,
                ClassificationType.WEB_SEARCH.value,
                ClassificationType.TIP.value,
            ]},
            label=RESPONSE_LABELS[ClassificationType.NAVIGATION.value]
        )
        result.scores[ClassificationType.NAVIGATION.value] = 0.85
        
        # Log classification with fast processing time
        log_classification(
            classification_result=result,
            user_message="How do I create a company?",
            user=self.user,
            processing_time_ms=150.0  # < 500ms
        )
        
        # Flush log handler
        self.log_handler.flush()
        
        # Check that no performance warning was logged
        log_records = [record for record in self.logger.handlers[0].buffer]
        performance_warnings = [
            record for record in log_records
            if record.levelname == 'WARNING' and 'PERFORMANCE WARNING' in record.message
        ]
        
        self.assertEqual(len(performance_warnings), 0, "No performance warning should be logged")
    
    def test_low_confidence_warning_logged(self):
        """Test that low confidence warning is logged for confidence < 0.6."""
        # Create classification result with low confidence
        result = ClassificationResult(
            type=ClassificationType.TIP.value,
            confidence=0.45,
            scores={
                ClassificationType.NAVIGATION.value: 0.35,
                ClassificationType.FEATURE_GUIDE.value: 0.30,
                ClassificationType.COMPANY_DATA.value: 0.25,
                ClassificationType.KENYA_GOVERNANCE.value: 0.20,
                ClassificationType.WEB_SEARCH.value: 0.40,
                ClassificationType.TIP.value: 0.45,
            },
            label=RESPONSE_LABELS[ClassificationType.TIP.value]
        )
        
        # Log classification
        log_classification(
            classification_result=result,
            user_message="I need help",
            user=self.user,
            processing_time_ms=100.0
        )
        
        # Flush log handler
        self.log_handler.flush()
        
        # Check that warning was logged
        log_records = [record for record in self.logger.handlers[0].buffer]
        confidence_warnings = [
            record for record in log_records
            if record.levelname == 'WARNING' and 'LOW CONFIDENCE WARNING' in record.message
        ]
        
        self.assertGreater(len(confidence_warnings), 0, "Low confidence warning should be logged")
        
        warning_message = confidence_warnings[0].message
        self.assertIn('0.45', warning_message)
        self.assertIn('threshold: 0.6', warning_message)
        self.assertIn('I need help', warning_message)
    
    def test_no_low_confidence_warning_for_high_confidence(self):
        """Test that no low confidence warning is logged for confidence >= 0.6."""
        # Create classification result with high confidence
        result = ClassificationResult(
            type=ClassificationType.NAVIGATION.value,
            confidence=0.85,
            scores={t: 0.0 for t in [
                ClassificationType.NAVIGATION.value,
                ClassificationType.FEATURE_GUIDE.value,
                ClassificationType.COMPANY_DATA.value,
                ClassificationType.KENYA_GOVERNANCE.value,
                ClassificationType.WEB_SEARCH.value,
                ClassificationType.TIP.value,
            ]},
            label=RESPONSE_LABELS[ClassificationType.NAVIGATION.value]
        )
        result.scores[ClassificationType.NAVIGATION.value] = 0.85
        
        # Log classification
        log_classification(
            classification_result=result,
            user_message="How do I create a company?",
            user=self.user,
            processing_time_ms=100.0
        )
        
        # Flush log handler
        self.log_handler.flush()
        
        # Check that no low confidence warning was logged
        log_records = [record for record in self.logger.handlers[0].buffer]
        confidence_warnings = [
            record for record in log_records
            if record.levelname == 'WARNING' and 'LOW CONFIDENCE WARNING' in record.message
        ]
        
        self.assertEqual(len(confidence_warnings), 0, "No low confidence warning should be logged")
    
    def test_both_warnings_logged_for_slow_low_confidence(self):
        """Test that both warnings are logged for slow + low confidence classification."""
        # Create classification result with low confidence
        result = ClassificationResult(
            type=ClassificationType.TIP.value,
            confidence=0.45,
            scores={t: 0.0 for t in [
                ClassificationType.NAVIGATION.value,
                ClassificationType.FEATURE_GUIDE.value,
                ClassificationType.COMPANY_DATA.value,
                ClassificationType.KENYA_GOVERNANCE.value,
                ClassificationType.WEB_SEARCH.value,
                ClassificationType.TIP.value,
            ]},
            label=RESPONSE_LABELS[ClassificationType.TIP.value]
        )
        result.scores[ClassificationType.TIP.value] = 0.45
        
        # Log classification with slow processing time
        log_classification(
            classification_result=result,
            user_message="I need help",
            user=self.user,
            processing_time_ms=600.0  # > 500ms
        )
        
        # Flush log handler
        self.log_handler.flush()
        
        # Check that both warnings were logged
        log_records = [record for record in self.logger.handlers[0].buffer]
        
        performance_warnings = [
            record for record in log_records
            if record.levelname == 'WARNING' and 'PERFORMANCE WARNING' in record.message
        ]
        
        confidence_warnings = [
            record for record in log_records
            if record.levelname == 'WARNING' and 'LOW CONFIDENCE WARNING' in record.message
        ]
        
        self.assertGreater(len(performance_warnings), 0, "Performance warning should be logged")
        self.assertGreater(len(confidence_warnings), 0, "Low confidence warning should be logged")
    
    def test_log_classification_handles_missing_user(self):
        """Test that log_classification works without a user."""
        # Create classification result
        result = ClassificationResult(
            type=ClassificationType.NAVIGATION.value,
            confidence=0.85,
            scores={t: 0.0 for t in [
                ClassificationType.NAVIGATION.value,
                ClassificationType.FEATURE_GUIDE.value,
                ClassificationType.COMPANY_DATA.value,
                ClassificationType.KENYA_GOVERNANCE.value,
                ClassificationType.WEB_SEARCH.value,
                ClassificationType.TIP.value,
            ]},
            label=RESPONSE_LABELS[ClassificationType.NAVIGATION.value]
        )
        result.scores[ClassificationType.NAVIGATION.value] = 0.85
        
        # Log classification without user
        log_classification(
            classification_result=result,
            user_message="How do I create a company?",
            user=None,
            processing_time_ms=150.0
        )
        
        # Verify database entry created
        self.assertEqual(ClassificationLog.objects.count(), 1)
        
        log_entry = ClassificationLog.objects.first()
        self.assertIsNone(log_entry.user)
        self.assertEqual(log_entry.message, "How do I create a company?")
    
    def test_log_classification_handles_missing_context(self):
        """Test that log_classification works without context data."""
        # Create classification result
        result = ClassificationResult(
            type=ClassificationType.NAVIGATION.value,
            confidence=0.85,
            scores={t: 0.0 for t in [
                ClassificationType.NAVIGATION.value,
                ClassificationType.FEATURE_GUIDE.value,
                ClassificationType.COMPANY_DATA.value,
                ClassificationType.KENYA_GOVERNANCE.value,
                ClassificationType.WEB_SEARCH.value,
                ClassificationType.TIP.value,
            ]},
            label=RESPONSE_LABELS[ClassificationType.NAVIGATION.value]
        )
        result.scores[ClassificationType.NAVIGATION.value] = 0.85
        
        # Log classification without context
        log_classification(
            classification_result=result,
            user_message="How do I create a company?",
            user=self.user,
            processing_time_ms=150.0,
            context_data=None
        )
        
        # Verify database entry created with empty context
        self.assertEqual(ClassificationLog.objects.count(), 1)
        
        log_entry = ClassificationLog.objects.first()
        self.assertEqual(log_entry.context_data, {})
