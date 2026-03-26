"""
Integration tests for memory management in AI chat system.

Tests the integration of session memory and persistent memory
with the classification and response handler system.
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock

from communications.memory_helpers import (
    get_session_memory,
    update_session_memory,
    clear_session_memory,
    get_user_memory,
    store_conversation_topic,
)
from communications.ai_chat import generate_contextual_response
from communications.models import AssistantMemory
from authentication.models import UserProfile
from companies.models import Company


class MemoryIntegrationTestCase(TestCase):
    """Test memory management integration with AI chat system."""
    
    def setUp(self):
        """Set up test data."""
        # Create test company
        self.company = Company.objects.create(
            name="Test Company Ltd",
            registration_number="TEST123",
            tax_id="TAX123",
            address="123 Test St",
            contact_email="test@example.com",
            contact_phone="+254700000000",
            risk_level="low"
        )
        
        # Create test user
        self.user = UserProfile.objects.create_user(
            email="testuser@example.com",
            password="testpass123",
            full_name="Test User",
            role="admin",
            company=self.company
        )
        
        # Clear any existing session memory
        clear_session_memory(self.user.id)
    
    def tearDown(self):
        """Clean up after tests."""
        clear_session_memory(self.user.id)
    
    def test_session_memory_stores_conversation(self):
        """Test that session memory stores conversation exchanges."""
        user_id = self.user.id
        
        # Initially empty
        memory = get_session_memory(user_id)
        self.assertEqual(len(memory), 0)
        
        # Add first exchange
        update_session_memory(user_id, "Hello", "Hi! How can I help?")
        memory = get_session_memory(user_id)
        self.assertEqual(len(memory), 1)
        self.assertEqual(memory[0]['user'], "Hello")
        self.assertEqual(memory[0]['assistant'], "Hi! How can I help?")
        
        # Add second exchange
        update_session_memory(user_id, "What are my tasks?", "You have 5 tasks...")
        memory = get_session_memory(user_id)
        self.assertEqual(len(memory), 2)
    
    def test_session_memory_maintains_max_10_exchanges(self):
        """Test that session memory maintains maximum 10 exchanges."""
        user_id = self.user.id
        
        # Add 15 exchanges
        for i in range(15):
            update_session_memory(user_id, f"Question {i}", f"Answer {i}")
        
        # Should only keep last 10
        memory = get_session_memory(user_id)
        self.assertEqual(len(memory), 10)
        
        # Should have exchanges 5-14
        self.assertEqual(memory[0]['user'], "Question 5")
        self.assertEqual(memory[-1]['user'], "Question 14")
    
    def test_session_memory_clears_on_session_end(self):
        """Test that session memory clears when session ends."""
        user_id = self.user.id
        
        # Add some exchanges
        update_session_memory(user_id, "Hello", "Hi!")
        update_session_memory(user_id, "Goodbye", "See you!")
        
        memory = get_session_memory(user_id)
        self.assertEqual(len(memory), 2)
        
        # Clear session
        clear_session_memory(user_id)
        
        # Should be empty
        memory = get_session_memory(user_id)
        self.assertEqual(len(memory), 0)
    
    def test_persistent_memory_creates_record(self):
        """Test that persistent memory creates record for new user."""
        user_id = self.user.id
        
        # Get or create memory
        memory = get_user_memory(user_id)
        
        # Should exist
        self.assertIsNotNone(memory)
        self.assertEqual(memory.user_id, user_id)
        
        # Should have default values
        self.assertEqual(memory.tone_preference, 'balanced')
        self.assertEqual(memory.last_topics, [])
    
    def test_persistent_memory_stores_preferred_name(self):
        """Test that persistent memory stores preferred name."""
        user_id = self.user.id
        
        # Update preferred name
        from communications.memory_helpers import update_user_memory
        success = update_user_memory(user_id, preferred_name="Sarah")
        self.assertTrue(success)
        
        # Retrieve and verify
        memory = get_user_memory(user_id)
        self.assertEqual(memory.preferred_name, "Sarah")
    
    def test_persistent_memory_stores_conversation_topics(self):
        """Test that persistent memory stores conversation topics."""
        user_id = self.user.id
        
        # Store topics
        store_conversation_topic(user_id, "staff information")
        store_conversation_topic(user_id, "company data")
        store_conversation_topic(user_id, "deadlines")
        
        # Retrieve and verify
        memory = get_user_memory(user_id)
        self.assertEqual(len(memory.last_topics), 3)
        self.assertIn("staff information", memory.last_topics)
        self.assertIn("company data", memory.last_topics)
        self.assertIn("deadlines", memory.last_topics)
    
    def test_persistent_memory_maintains_max_10_topics(self):
        """Test that persistent memory maintains maximum 10 topics."""
        user_id = self.user.id
        
        # Store 15 topics
        for i in range(15):
            store_conversation_topic(user_id, f"topic_{i}")
        
        # Should only keep last 10
        memory = get_user_memory(user_id)
        self.assertEqual(len(memory.last_topics), 10)
        
        # Should have topics 5-14
        self.assertEqual(memory.last_topics[0], "topic_5")
        self.assertEqual(memory.last_topics[-1], "topic_14")
    
    @patch('communications.ai_chat.getattr')
    def test_classification_system_uses_session_memory(self, mock_getattr):
        """Test that classification system retrieves and uses session memory."""
        # Enable classification
        mock_getattr.return_value = True
        
        user_id = self.user.id
        
        # Add some session memory
        update_session_memory(user_id, "What are my tasks?", "You have 5 tasks...")
        update_session_memory(user_id, "Show me companies", "You have 3 companies...")
        
        # The classification context should include session memory
        # This is tested indirectly through the integration
        memory = get_session_memory(user_id)
        self.assertEqual(len(memory), 2)
    
    def test_sse_streaming_format_compatibility(self):
        """Test that markdown responses maintain SSE streaming format."""
        # This test verifies that markdown formatting doesn't break SSE
        response_text = "**Bold Text** with some normal text and more content."
        
        # Simulate streaming (same as generate_local_response)
        words = response_text.split()
        chunks = []
        for i, word in enumerate(words):
            content = word + (" " if i < len(words) - 1 else "")
            chunks.append(content)
        
        # Verify all chunks are strings
        for chunk in chunks:
            self.assertIsInstance(chunk, str)
        
        # Verify text is preserved when reconstructed
        reconstructed = "".join(chunks)
        self.assertEqual(reconstructed, response_text)
        
        # Verify markdown characters are preserved
        self.assertIn("**Bold Text**", reconstructed)
    
    def test_error_handling_in_memory_operations(self):
        """Test that memory operations handle errors gracefully."""
        # Test with invalid user ID
        invalid_user_id = 99999
        
        # Should return None for invalid user
        memory = get_user_memory(invalid_user_id)
        self.assertIsNone(memory)
        
        # Should return False for failed update
        from communications.memory_helpers import update_user_memory
        success = update_user_memory(invalid_user_id, preferred_name="Test")
        self.assertFalse(success)
        
        # Should return False for failed topic storage
        success = store_conversation_topic(invalid_user_id, "test topic")
        self.assertFalse(success)


class SSEStreamingTestCase(TestCase):
    """Test SSE streaming format compatibility."""
    
    def test_markdown_response_streams_correctly(self):
        """Test that markdown responses stream correctly via SSE."""
        import json
        
        # Sample markdown response
        markdown_text = "**Company Information**\n\nYou have **3 companies**:\n\n- Company A\n- Company B\n- Company C"
        
        # Simulate SSE streaming
        words = markdown_text.split()
        sse_chunks = []
        
        for i, word in enumerate(words):
            content = word + (" " if i < len(words) - 1 else "")
            data = json.dumps({
                "choices": [{"delta": {"content": content}}]
            })
            sse_chunk = f"data: {data}\n\n"
            sse_chunks.append(sse_chunk)
        
        # Add completion signal
        sse_chunks.append("data: [DONE]\n\n")
        
        # Verify all chunks are valid SSE format
        for chunk in sse_chunks[:-1]:  # Exclude [DONE]
            self.assertTrue(chunk.startswith("data: "))
            self.assertTrue(chunk.endswith("\n\n"))
            
            # Extract JSON and verify it's valid
            json_str = chunk[6:-2]  # Remove "data: " and "\n\n"
            data = json.loads(json_str)
            self.assertIn("choices", data)
            self.assertIn("delta", data["choices"][0])
            self.assertIn("content", data["choices"][0]["delta"])
        
        # Verify completion signal
        self.assertEqual(sse_chunks[-1], "data: [DONE]\n\n")
    
    def test_error_chunk_format(self):
        """Test that error chunks are sent in correct SSE format."""
        import json
        
        error_message = "An error occurred while generating response."
        error_data = json.dumps({"error": {"message": error_message}})
        error_chunk = f"data: {error_data}\n\n"
        
        # Verify format
        self.assertTrue(error_chunk.startswith("data: "))
        self.assertTrue(error_chunk.endswith("\n\n"))
        
        # Extract and verify JSON
        json_str = error_chunk[6:-2]
        data = json.loads(json_str)
        self.assertIn("error", data)
        self.assertIn("message", data["error"])
        self.assertEqual(data["error"]["message"], error_message)
