"""
Simplified Integration tests for the AI Message Classification System.

This module implements streamlined integration tests covering:
- End-to-end message → classification → routing → response flow
- Fallback activation on low confidence
- Label prepending in response
- Error handling doesn't break chat

Tests are optimized for speed and don't require complex database setup.
"""

import json
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from django.test import TestCase

from communications.classifier import (
    MessageClassifier,
    ClassificationResult,
    ClassificationContext,
    get_classifier,
    reset_classifier,
    get_routing_engine,
    reset_routing_engine
)
from communications.response_handlers import get_handler


class TestSimpleIntegrationFlow(TestCase):
    """Simplified integration tests for end-to-end classification and routing."""
    
    def setUp(self):
        """Set up test fixtures."""
        reset_classifier()
        reset_routing_engine()
        self.classifier = get_classifier()
        self.routing_engine = get_routing_engine()
        
        # Load keyword dictionaries
        from communications.classification_keywords import get_keyword_dictionaries
        keywords = get_keyword_dictionaries()
        self.classifier.load_keywords(keywords)
        
        # Register response handlers with routing engine
        from communications.response_handlers import RESPONSE_HANDLERS
        for classification_type, handler in RESPONSE_HANDLERS.items():
            self.routing_engine.register_handler(classification_type, handler)
        
        # Load test dataset for integration testing
        test_dataset_path = Path(__file__).parent / "test_dataset.json"
        with open(test_dataset_path, 'r') as f:
            self.test_dataset = json.load(f)
    
    def tearDown(self):
        """Clean up after tests."""
        reset_classifier()
        reset_routing_engine()
    
    # ============================================================================
    # Core End-to-End Flow Tests
    # ============================================================================
    
    def test_end_to_end_classification_flow(self):
        """
        Test complete flow: message → classification → routing → response
        """
        test_cases = [
            {
                "message": "How do I create a new company?",
                "expected_type": "Navigation",
                "expected_label": "→"
            },
            {
                "message": "What does the compliance score feature do?",
                "expected_type": "Feature_Guide", 
                "expected_label": "?"
            },
            {
                "message": "What are the CMA requirements for annual returns?",
                "expected_type": "Kenya_Governance",
                "expected_label": "⚖"
            },
            {
                "message": "What is the capital of Kenya?",
                "expected_type": "Web_Search",
                "expected_label": "⊕"
            },
            {
                "message": "I am confused",
                "expected_type": "Tip",
                "expected_label": "!"
            }
        ]
        
        for test_case in test_cases:
            with self.subTest(message=test_case["message"]):
                message = test_case["message"]
                context = ClassificationContext()
                
                # Step 1: Classification
                classification = self.classifier.classify(message, context)
                
                # Step 2: Routing (without user object for simplicity)
                response = self.routing_engine.route(
                    classification=classification,
                    user_message=message,
                    user=None
                )
                
                # Verify response is valid
                self.assertIsInstance(response, str)
                self.assertTrue(len(response) > 0)
                
                # Verify label is prepended
                self.assertTrue(
                    response.startswith(test_case["expected_label"]),
                    f"Response should start with '{test_case['expected_label']}', "
                    f"got: '{response[:10]}...'"
                )
                
                # Log results for debugging
                print(f"\nTest: {message}")
                print(f"  Expected: {test_case['expected_type']} ({test_case['expected_label']})")
                print(f"  Actual: {classification.type} ({classification.label}) - conf: {classification.confidence:.2f}")
                print(f"  Response: {response[:100]}...")
    
    def test_fallback_activation_low_confidence(self):
        """
        Test that fallback handler is activated when confidence is low
        """
        # Use a message that should have low confidence
        message = "xyz random words that match nothing"
        context = ClassificationContext()
        
        # Classification
        classification = self.classifier.classify(message, context)
        
        # Routing
        response = self.routing_engine.route(
            classification=classification,
            user_message=message,
            user=None
        )
        
        # Verify fallback response
        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)
        
        # Should use fallback label (!)
        self.assertTrue(response.startswith("!"))
        
        print(f"\nFallback Test: {message}")
        print(f"  Classification: {classification.type} - conf: {classification.confidence:.2f}")
        print(f"  Response: {response[:100]}...")
    
    def test_all_classification_types_work(self):
        """
        Test that all six classification types can be triggered and produce responses
        """
        # Use messages from test dataset that should trigger each type
        type_messages = {
            "Navigation": "How do I create a company?",
            "Feature_Guide": "What does this feature do?", 
            "Company_Data": "What is my company score?",
            "Kenya_Governance": "What are CMA requirements?",
            "Web_Search": "What is the weather?",
            "Tip": "I need help"
        }
        
        results = {}
        
        for expected_type, message in type_messages.items():
            context = ClassificationContext()
            classification = self.classifier.classify(message, context)
            response = self.routing_engine.route(classification, message, None)
            
            results[expected_type] = {
                'message': message,
                'actual_type': classification.type,
                'confidence': classification.confidence,
                'response_length': len(response),
                'has_label': len(response) > 0 and response[0] in ['→', '?', '◈', '⚖', '⊕', '!']
            }
            
            # Verify response is valid
            self.assertIsInstance(response, str)
            self.assertTrue(len(response) > 0)
            self.assertTrue(results[expected_type]['has_label'])
        
        # Print results for debugging
        print("\nClassification Type Test Results:")
        for type_name, result in results.items():
            print(f"  {type_name}:")
            print(f"    Message: {result['message']}")
            print(f"    Classified as: {result['actual_type']} (conf: {result['confidence']:.2f})")
            print(f"    Response length: {result['response_length']}")
            print(f"    Has label: {result['has_label']}")
    
    # ============================================================================
    # Performance Tests
    # ============================================================================
    
    def test_end_to_end_performance(self):
        """
        Test that end-to-end flow meets performance requirements
        """
        message = "How do I create a new company?"
        context = ClassificationContext()
        
        # Measure total time for classification + routing
        start_time = time.perf_counter()
        
        classification = self.classifier.classify(message, context)
        response = self.routing_engine.route(classification, message, None)
        
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        
        # End-to-end should be fast (within 300ms for single message)
        self.assertLess(total_time_ms, 300.0, 
                       f"End-to-end flow too slow: {total_time_ms:.2f}ms")
        
        # Verify we got valid results
        self.assertIsInstance(classification, ClassificationResult)
        self.assertIsInstance(response, str)
        self.assertTrue(len(response) > 0)
        
        print(f"\nPerformance Test:")
        print(f"  Total time: {total_time_ms:.2f}ms")
        print(f"  Classification: {classification.type} (conf: {classification.confidence:.2f})")
        print(f"  Response length: {len(response)}")
    
    def test_batch_processing_performance(self):
        """
        Test processing multiple messages for performance
        """
        # Use first 10 messages from test dataset for speed
        test_messages = [case['message'] for case in self.test_dataset[:10]]
        
        results = []
        total_time = 0
        
        for message in test_messages:
            context = ClassificationContext()
            
            start_time = time.perf_counter()
            
            try:
                classification = self.classifier.classify(message, context)
                response = self.routing_engine.route(classification, message, None)
                
                end_time = time.perf_counter()
                processing_time = (end_time - start_time) * 1000
                total_time += processing_time
                
                results.append({
                    'message': message[:50] + "..." if len(message) > 50 else message,
                    'type': classification.type,
                    'confidence': classification.confidence,
                    'response_length': len(response),
                    'time_ms': processing_time
                })
                
            except Exception as e:
                self.fail(f"Batch processing failed for message '{message}': {e}")
        
        # Verify all messages processed successfully
        self.assertEqual(len(results), len(test_messages))
        
        # Verify average performance
        avg_time = total_time / len(results)
        self.assertLess(avg_time, 200.0, 
                       f"Average processing time too slow: {avg_time:.2f}ms")
        
        print(f"\nBatch Processing Test:")
        print(f"  Messages processed: {len(results)}")
        print(f"  Total time: {total_time:.2f}ms")
        print(f"  Average time: {avg_time:.2f}ms")
        print(f"  Fastest: {min(r['time_ms'] for r in results):.2f}ms")
        print(f"  Slowest: {max(r['time_ms'] for r in results):.2f}ms")
    
    # ============================================================================
    # Error Handling Tests
    # ============================================================================
    
    def test_error_handling_doesnt_break_system(self):
        """
        Test that classification errors don't break the system
        """
        # Test with potentially problematic inputs
        problematic_messages = [
            "",  # Empty message
            " ",  # Whitespace only
            "a" * 500,  # Very long message
            "🚀🎉💻",  # Emoji only
            "SELECT * FROM users;",  # SQL-like content
            "<script>alert('test')</script>",  # HTML-like content
        ]
        
        for message in problematic_messages:
            with self.subTest(message=message[:50]):
                try:
                    context = ClassificationContext()
                    classification = self.classifier.classify(message, context)
                    response = self.routing_engine.route(classification, message, None)
                    
                    # Should always return a string response
                    self.assertIsInstance(response, str)
                    
                    # Should not be empty for non-empty messages
                    if message.strip():
                        self.assertTrue(len(response.strip()) > 0)
                        
                except Exception as e:
                    self.fail(f"Error handling failed for message '{message[:50]}': {e}")
    
    def test_classification_consistency(self):
        """
        Test that same message produces consistent results
        """
        message = "How do I create a new company?"
        context = ClassificationContext()
        
        # Classify the same message multiple times
        results = []
        for i in range(5):
            classification = self.classifier.classify(message, context)
            results.append({
                'type': classification.type,
                'confidence': classification.confidence,
                'label': classification.label
            })
        
        # All results should be identical
        first_result = results[0]
        for i, result in enumerate(results[1:], 1):
            self.assertEqual(result['type'], first_result['type'],
                           f"Classification type inconsistent on attempt {i+1}")
            self.assertAlmostEqual(result['confidence'], first_result['confidence'], places=3,
                                 msg=f"Confidence inconsistent on attempt {i+1}")
            self.assertEqual(result['label'], first_result['label'],
                           f"Label inconsistent on attempt {i+1}")
        
        print(f"\nConsistency Test:")
        print(f"  Message: {message}")
        print(f"  Consistent type: {first_result['type']}")
        print(f"  Consistent confidence: {first_result['confidence']:.3f}")
        print(f"  Consistent label: {first_result['label']}")
    
    # ============================================================================
    # Context and Boost Tests
    # ============================================================================
    
    def test_context_boosts_work(self):
        """
        Test that context boosts affect classification confidence
        """
        test_cases = [
            {
                "message": "What about my company directors?",
                "expected_boost_type": "Company_Data",
                "boost_reason": "contains 'my company'"
            },
            {
                "message": "Tell me about BRS requirements",
                "expected_boost_type": "Kenya_Governance", 
                "boost_reason": "contains 'BRS'"
            },
            {
                "message": "What are the CMA guidelines?",
                "expected_boost_type": "Kenya_Governance",
                "boost_reason": "contains 'CMA'"
            }
        ]
        
        for test_case in test_cases:
            with self.subTest(message=test_case["message"]):
                context = ClassificationContext()
                classification = self.classifier.classify(test_case["message"], context)
                
                # Check if the expected type got a boost
                boosted_confidence = classification.scores.get(test_case["expected_boost_type"], 0)
                
                # Should have some confidence for the boosted type
                self.assertGreater(boosted_confidence, 0.0,
                                 f"Expected boost for {test_case['expected_boost_type']} "
                                 f"due to {test_case['boost_reason']}")
                
                print(f"\nContext Boost Test:")
                print(f"  Message: {test_case['message']}")
                print(f"  Expected boost: {test_case['expected_boost_type']}")
                print(f"  Actual confidence: {boosted_confidence:.3f}")
                print(f"  Final classification: {classification.type} (conf: {classification.confidence:.3f})")
    
    # ============================================================================
    # Label Verification Tests
    # ============================================================================
    
    def test_correct_labels_used(self):
        """
        Test that correct labels are used for each classification type
        """
        expected_labels = {
            "Navigation": "→",
            "Feature_Guide": "?", 
            "Company_Data": "◈",
            "Kenya_Governance": "⚖",
            "Web_Search": "⊕",
            "Tip": "!"
        }
        
        # Test each type with a message that should trigger it
        type_messages = {
            "Navigation": "How do I access the dashboard?",
            "Feature_Guide": "What does the compliance feature do?",
            "Company_Data": "Show me my company information", 
            "Kenya_Governance": "What are the CMA requirements?",
            "Web_Search": "What is the weather today?",
            "Tip": "I am confused about something"
        }
        
        for classification_type, message in type_messages.items():
            with self.subTest(type=classification_type):
                context = ClassificationContext()
                classification = self.classifier.classify(message, context)
                response = self.routing_engine.route(classification, message, None)
                
                expected_label = expected_labels[classification_type]
                
                # Response should start with the correct label
                self.assertTrue(
                    response.startswith(expected_label),
                    f"Response for {classification_type} should start with '{expected_label}', "
                    f"got: '{response[:10]}...'"
                )
                
                # Classification should have the correct label
                if classification.type == classification_type:
                    self.assertEqual(classification.label, expected_label,
                                   f"Classification label should be '{expected_label}' "
                                   f"for type {classification_type}")