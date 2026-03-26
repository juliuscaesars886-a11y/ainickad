"""
Unit tests for memory management helper functions.

Tests both session memory (in-memory) and persistent memory (database) functions.
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from communications.memory_helpers import (
    get_session_memory,
    update_session_memory,
    clear_session_memory,
    get_user_memory,
    update_user_memory,
    store_conversation_topic,
    _session_memory
)
from communications.models import AssistantMemory
from authentication.models import UserProfile


class SessionMemoryTestCase(TestCase):
    """Test cases for session memory functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Clear session memory before each test
        _session_memory.clear()
    
    def test_get_session_memory_empty(self):
        """Test get_session_memory returns empty list for new user."""
        memory = get_session_memory(999)
        self.assertEqual(memory, [])
    
    def test_update_session_memory_single_exchange(self):
        """Test update_session_memory stores single message exchange."""
        user_id = 1
        user_msg = "Hello"
        assistant_msg = "Hi! How can I help?"
        
        update_session_memory(user_id, user_msg, assistant_msg)
        
        memory = get_session_memory(user_id)
        self.assertEqual(len(memory), 1)
        self.assertEqual(memory[0]['user'], user_msg)
        self.assertEqual(memory[0]['assistant'], assistant_msg)
        self.assertIn('timestamp', memory[0])
    
    def test_update_session_memory_multiple_exchanges(self):
        """Test update_session_memory stores multiple exchanges."""
        user_id = 1
        
        for i in range(5):
            update_session_memory(user_id, f"Message {i}", f"Response {i}")
        
        memory = get_session_memory(user_id)
        self.assertEqual(len(memory), 5)
        self.assertEqual(memory[0]['user'], "Message 0")
        self.assertEqual(memory[4]['user'], "Message 4")
    
    def test_update_session_memory_max_10_exchanges(self):
        """Test update_session_memory maintains max 10 exchanges."""
        user_id = 1
        
        # Add 15 exchanges
        for i in range(15):
            update_session_memory(user_id, f"Message {i}", f"Response {i}")
        
        memory = get_session_memory(user_id)
        
        # Should only keep last 10
        self.assertEqual(len(memory), 10)
        
        # First message should be "Message 5" (oldest of the last 10)
        self.assertEqual(memory[0]['user'], "Message 5")
        
        # Last message should be "Message 14"
        self.assertEqual(memory[9]['user'], "Message 14")
    
    def test_clear_session_memory(self):
        """Test clear_session_memory removes all data."""
        user_id = 1
        
        # Add some exchanges
        update_session_memory(user_id, "Hello", "Hi")
        update_session_memory(user_id, "How are you?", "I'm good!")
        
        # Verify data exists
        self.assertEqual(len(get_session_memory(user_id)), 2)
        
        # Clear memory
        clear_session_memory(user_id)
        
        # Verify data is gone
        self.assertEqual(len(get_session_memory(user_id)), 0)
    
    def test_clear_session_memory_nonexistent_user(self):
        """Test clear_session_memory handles nonexistent user gracefully."""
        # Should not raise error
        clear_session_memory(999)
    
    def test_session_memory_isolation(self):
        """Test session memory is isolated between users."""
        user1_id = 1
        user2_id = 2
        
        update_session_memory(user1_id, "User 1 message", "Response 1")
        update_session_memory(user2_id, "User 2 message", "Response 2")
        
        memory1 = get_session_memory(user1_id)
        memory2 = get_session_memory(user2_id)
        
        self.assertEqual(len(memory1), 1)
        self.assertEqual(len(memory2), 1)
        self.assertEqual(memory1[0]['user'], "User 1 message")
        self.assertEqual(memory2[0]['user'], "User 2 message")


class PersistentMemoryTestCase(TestCase):
    """Test cases for persistent memory functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Import Company model
        from companies.models import Company
        
        # Create test company first
        self.company = Company.objects.create(
            name='Test Company',
            registration_number='TEST123',
            tax_id='TAX123',
            address='123 Test St',
            contact_email='test@company.com',
            contact_phone='+254700000000'
        )
        
        # Create test user with company
        self.user = UserProfile.objects.create(
            email='test@example.com',
            full_name='Test User',
            role='staff',
            company=self.company
        )
    
    def tearDown(self):
        """Clean up test data."""
        AssistantMemory.objects.all().delete()
        UserProfile.objects.all().delete()
        from companies.models import Company
        Company.objects.all().delete()
    
    def test_get_user_memory_creates_new_record(self):
        """Test get_user_memory creates new record if none exists."""
        memory = get_user_memory(self.user.id)
        
        self.assertIsNotNone(memory)
        self.assertEqual(memory.user, self.user)
        self.assertEqual(memory.tone_preference, 'balanced')
        self.assertEqual(memory.last_topics, [])
    
    def test_get_user_memory_retrieves_existing_record(self):
        """Test get_user_memory retrieves existing record."""
        # Create memory record
        AssistantMemory.objects.create(
            user=self.user,
            preferred_name='Tester',
            tone_preference='casual'
        )
        
        memory = get_user_memory(self.user.id)
        
        self.assertIsNotNone(memory)
        self.assertEqual(memory.preferred_name, 'Tester')
        self.assertEqual(memory.tone_preference, 'casual')
    
    def test_get_user_memory_invalid_user(self):
        """Test get_user_memory returns None for invalid user."""
        memory = get_user_memory(99999)
        self.assertIsNone(memory)
    
    def test_update_user_memory_preferred_name(self):
        """Test update_user_memory updates preferred name."""
        success = update_user_memory(self.user.id, preferred_name='Sarah')
        
        self.assertTrue(success)
        
        memory = AssistantMemory.objects.get(user=self.user)
        self.assertEqual(memory.preferred_name, 'Sarah')
    
    def test_update_user_memory_tone_preference(self):
        """Test update_user_memory updates tone preference."""
        success = update_user_memory(self.user.id, tone_preference='formal')
        
        self.assertTrue(success)
        
        memory = AssistantMemory.objects.get(user=self.user)
        self.assertEqual(memory.tone_preference, 'formal')
    
    def test_update_user_memory_role_context(self):
        """Test update_user_memory updates role context."""
        context = "Senior accountant responsible for financial reporting"
        success = update_user_memory(self.user.id, role_context=context)
        
        self.assertTrue(success)
        
        memory = AssistantMemory.objects.get(user=self.user)
        self.assertEqual(memory.role_context, context)
    
    def test_update_user_memory_multiple_fields(self):
        """Test update_user_memory updates multiple fields."""
        success = update_user_memory(
            self.user.id,
            preferred_name='John',
            tone_preference='casual',
            role_context='IT Specialist'
        )
        
        self.assertTrue(success)
        
        memory = AssistantMemory.objects.get(user=self.user)
        self.assertEqual(memory.preferred_name, 'John')
        self.assertEqual(memory.tone_preference, 'casual')
        self.assertEqual(memory.role_context, 'IT Specialist')
    
    def test_update_user_memory_partial_update(self):
        """Test update_user_memory only updates provided fields."""
        # Create initial memory
        AssistantMemory.objects.create(
            user=self.user,
            preferred_name='Original',
            tone_preference='formal'
        )
        
        # Update only preferred_name
        success = update_user_memory(self.user.id, preferred_name='Updated')
        
        self.assertTrue(success)
        
        memory = AssistantMemory.objects.get(user=self.user)
        self.assertEqual(memory.preferred_name, 'Updated')
        self.assertEqual(memory.tone_preference, 'formal')  # Unchanged
    
    def test_update_user_memory_invalid_user(self):
        """Test update_user_memory returns False for invalid user."""
        success = update_user_memory(99999, preferred_name='Test')
        self.assertFalse(success)
    
    def test_store_conversation_topic_single(self):
        """Test store_conversation_topic stores single topic."""
        success = store_conversation_topic(self.user.id, 'staff information')
        
        self.assertTrue(success)
        
        memory = AssistantMemory.objects.get(user=self.user)
        self.assertEqual(len(memory.last_topics), 1)
        self.assertEqual(memory.last_topics[0], 'staff information')
    
    def test_store_conversation_topic_multiple(self):
        """Test store_conversation_topic stores multiple topics."""
        topics = ['staff', 'companies', 'documents', 'tasks', 'templates']
        
        for topic in topics:
            success = store_conversation_topic(self.user.id, topic)
            self.assertTrue(success)
        
        memory = AssistantMemory.objects.get(user=self.user)
        self.assertEqual(len(memory.last_topics), 5)
        self.assertEqual(memory.last_topics, topics)
    
    def test_store_conversation_topic_max_10(self):
        """Test store_conversation_topic maintains max 10 topics."""
        # Store 15 topics
        for i in range(15):
            store_conversation_topic(self.user.id, f'topic_{i}')
        
        memory = AssistantMemory.objects.get(user=self.user)
        
        # Should only keep last 10
        self.assertEqual(len(memory.last_topics), 10)
        
        # First topic should be 'topic_5' (oldest of the last 10)
        self.assertEqual(memory.last_topics[0], 'topic_5')
        
        # Last topic should be 'topic_14'
        self.assertEqual(memory.last_topics[9], 'topic_14')
    
    def test_store_conversation_topic_invalid_user(self):
        """Test store_conversation_topic returns False for invalid user."""
        success = store_conversation_topic(99999, 'test topic')
        self.assertFalse(success)
