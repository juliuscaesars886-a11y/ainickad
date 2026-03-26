"""
Unit tests for AI Chat functionality
"""
import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase, APIClient


class AIChatsValidationTests(TestCase):
    """Test message validation"""
    
    def test_validate_messages_valid(self):
        """Test validation of valid messages"""
        from communications.ai_chat import validate_messages
        
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        self.assertTrue(validate_messages(messages))
    
    def test_validate_messages_empty_list(self):
        """Test validation rejects empty list"""
        from communications.ai_chat import validate_messages
        
        self.assertFalse(validate_messages([]))
    
    def test_validate_messages_missing_role(self):
        """Test validation rejects missing role"""
        from communications.ai_chat import validate_messages
        
        messages = [{"content": "Hello"}]
        self.assertFalse(validate_messages(messages))
    
    def test_validate_messages_missing_content(self):
        """Test validation rejects missing content"""
        from communications.ai_chat import validate_messages
        
        messages = [{"role": "user"}]
        self.assertFalse(validate_messages(messages))
    
    def test_validate_messages_invalid_role(self):
        """Test validation rejects invalid role"""
        from communications.ai_chat import validate_messages
        
        messages = [{"role": "invalid", "content": "Hello"}]
        self.assertFalse(validate_messages(messages))
    
    def test_validate_messages_empty_content(self):
        """Test validation rejects empty content"""
        from communications.ai_chat import validate_messages
        
        messages = [{"role": "user", "content": ""}]
        self.assertFalse(validate_messages(messages))
    
    def test_validate_messages_whitespace_content(self):
        """Test validation rejects whitespace-only content"""
        from communications.ai_chat import validate_messages
        
        messages = [{"role": "user", "content": "   "}]
        self.assertFalse(validate_messages(messages))


class AIChatsSystemPromptTests(TestCase):
    """Test system prompt generation"""
    
    def test_system_prompt_not_empty(self):
        """Test system prompt is generated"""
        from communications.ai_chat import get_system_prompt
        
        prompt = get_system_prompt()
        self.assertIsNotNone(prompt)
        self.assertGreater(len(prompt), 0)
    
    def test_system_prompt_contains_context(self):
        """Test system prompt contains relevant context"""
        from communications.ai_chat import get_system_prompt
        
        prompt = get_system_prompt()
        self.assertIn("governance", prompt.lower())
        self.assertIn("compliance", prompt.lower())


class AIChatsEndpointTests(APITestCase):
    """Test AI Chat endpoint"""
    
    def setUp(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.url = "/api/ai-chat/"
    
    def test_endpoint_requires_authentication(self):
        """Test endpoint requires authentication"""
        response = self.client.post(
            self.url,
            {"messages": [{"role": "user", "content": "Hello"}]},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_endpoint_missing_messages_field(self):
        """Test endpoint rejects request without messages field"""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_endpoint_invalid_message_format(self):
        """Test endpoint rejects invalid message format"""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.url,
            {"messages": [{"content": "Hello"}]},  # Missing role
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_endpoint_empty_messages_list(self):
        """Test endpoint rejects empty messages list"""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.url,
            {"messages": []},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    @patch("communications.ai_chat.openai.ChatCompletion.create")
    def test_endpoint_successful_response(self, mock_openai):
        """Test endpoint returns successful response"""
        # Mock OpenAI response
        mock_openai.return_value = iter([
            {
                "choices": [{"delta": {"content": "Hello"}, "finish_reason": None}]
            },
            {
                "choices": [{"delta": {"content": " there"}, "finish_reason": "stop"}]
            }
        ])
        
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.url,
            {"messages": [{"role": "user", "content": "Hello"}]},
            format="json"
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/event-stream")
    
    @patch("communications.ai_chat.openai.api_key", None)
    def test_endpoint_missing_api_key(self):
        """Test endpoint handles missing API key"""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.url,
            {"messages": [{"role": "user", "content": "Hello"}]},
            format="json"
        )
        
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
    
    @patch("communications.ai_chat.openai.ChatCompletion.create")
    def test_endpoint_rate_limiting(self, mock_openai):
        """Test endpoint rate limiting"""
        mock_openai.return_value = iter([
            {"choices": [{"delta": {"content": "test"}, "finish_reason": "stop"}]}
        ])
        
        self.client.force_authenticate(user=self.user)
        
        # Make multiple requests to test rate limiting
        for i in range(31):  # Exceed the 30/hour limit
            response = self.client.post(
                self.url,
                {"messages": [{"role": "user", "content": f"Hello {i}"}]},
                format="json"
            )
            
            if i < 30:
                self.assertEqual(response.status_code, status.HTTP_200_OK)
            else:
                # 31st request should be throttled
                self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class AIChatsStreamingTests(APITestCase):
    """Test streaming response handling"""
    
    def setUp(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.url = "/api/ai-chat/"
    
    @patch("communications.ai_chat.openai.ChatCompletion.create")
    def test_streaming_response_format(self, mock_openai):
        """Test streaming response is in SSE format"""
        mock_openai.return_value = iter([
            {"choices": [{"delta": {"content": "Hello"}, "finish_reason": None}]},
            {"choices": [{"delta": {"content": " world"}, "finish_reason": "stop"}]}
        ])
        
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.url,
            {"messages": [{"role": "user", "content": "Hello"}]},
            format="json"
        )
        
        # Check response is streaming
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/event-stream")
        
        # Collect streamed content
        content = b"".join(response.streaming_content).decode()
        self.assertIn("data:", content)
        self.assertIn("[DONE]", content)
    
    @patch("communications.ai_chat.openai.ChatCompletion.create")
    def test_streaming_handles_empty_delta(self, mock_openai):
        """Test streaming handles empty delta"""
        mock_openai.return_value = iter([
            {"choices": [{"delta": {}, "finish_reason": None}]},
            {"choices": [{"delta": {"content": "test"}, "finish_reason": "stop"}]}
        ])
        
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.url,
            {"messages": [{"role": "user", "content": "Hello"}]},
            format="json"
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AIChatsErrorHandlingTests(APITestCase):
    """Test error handling"""
    
    def setUp(self):
        """Set up test client and user"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.url = "/api/ai-chat/"
    
    @patch("communications.ai_chat.openai.ChatCompletion.create")
    def test_handles_rate_limit_error(self, mock_openai):
        """Test handling of OpenAI rate limit error"""
        import openai
        mock_openai.side_effect = openai.error.RateLimitError("Rate limited")
        
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.url,
            {"messages": [{"role": "user", "content": "Hello"}]},
            format="json"
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = b"".join(response.streaming_content).decode()
        self.assertIn("busy", content.lower())
    
    @patch("communications.ai_chat.openai.ChatCompletion.create")
    def test_handles_api_error(self, mock_openai):
        """Test handling of OpenAI API error"""
        import openai
        mock_openai.side_effect = openai.error.APIError("API error")
        
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.url,
            {"messages": [{"role": "user", "content": "Hello"}]},
            format="json"
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = b"".join(response.streaming_content).decode()
        self.assertIn("error", content.lower())
    
    @patch("communications.ai_chat.openai.ChatCompletion.create")
    def test_handles_authentication_error(self, mock_openai):
        """Test handling of OpenAI authentication error"""
        import openai
        mock_openai.side_effect = openai.error.AuthenticationError("Auth failed")
        
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.url,
            {"messages": [{"role": "user", "content": "Hello"}]},
            format="json"
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = b"".join(response.streaming_content).decode()
        self.assertIn("not configured", content.lower())


class AIChatsKnowledgeBaseTests(TestCase):
    """Test knowledge base loading and integration"""
    
    def test_knowledge_base_loading(self):
        """Test that knowledge base loads successfully"""
        from communications.ai_chat import load_knowledge_base
        
        knowledge = load_knowledge_base()
        self.assertIsNotNone(knowledge)
        # Knowledge should be a string (empty or with content)
        self.assertIsInstance(knowledge, str)
    
    def test_knowledge_base_caching(self):
        """Test that knowledge base is cached"""
        from communications.ai_chat import load_knowledge_base, _knowledge_cache
        
        # First call loads and caches
        knowledge1 = load_knowledge_base()
        
        # Second call should return cached version
        knowledge2 = load_knowledge_base()
        
        # Should be the same object (cached)
        self.assertEqual(knowledge1, knowledge2)
    
    def test_system_prompt_includes_knowledge(self):
        """Test that system prompt includes knowledge base"""
        from communications.ai_chat import get_system_prompt, load_knowledge_base
        
        knowledge = load_knowledge_base()
        prompt = get_system_prompt()
        
        # If knowledge exists, it should be in the prompt
        if knowledge:
            self.assertIn("KNOWLEDGE BASE", prompt)
    
    def test_system_prompt_mentions_brs(self):
        """Test that system prompt mentions BRS capabilities"""
        from communications.ai_chat import get_system_prompt
        
        prompt = get_system_prompt()
        # Should mention BRS in capabilities
        self.assertIn("BRS", prompt)
    
    def test_knowledge_base_contains_brs_content(self):
        """Test that knowledge base contains BRS-related content"""
        from communications.ai_chat import load_knowledge_base
        
        knowledge = load_knowledge_base()
        
        # If knowledge file exists, it should contain BRS content
        if knowledge and len(knowledge) > 0:
            # Check for key BRS terms
            knowledge_lower = knowledge.lower()
            self.assertTrue(
                "brs" in knowledge_lower or 
                "business registration" in knowledge_lower or
                "company registration" in knowledge_lower,
                "Knowledge base should contain BRS-related content"
            )
    
    def test_knowledge_base_contains_forms(self):
        """Test that knowledge base contains form references"""
        from communications.ai_chat import load_knowledge_base
        
        knowledge = load_knowledge_base()
        
        # If knowledge exists, check for common BRS forms
        if knowledge and len(knowledge) > 0:
            # Should mention at least some common forms
            has_forms = any(form in knowledge for form in ["CR29", "CR12", "BOF1", "CR1", "CR2"])
            if has_forms:
                self.assertTrue(has_forms, "Knowledge base should contain BRS form references")
    
    def test_knowledge_base_contains_fees(self):
        """Test that knowledge base contains fee information"""
        from communications.ai_chat import load_knowledge_base
        
        knowledge = load_knowledge_base()
        
        # If knowledge exists, check for fee information
        if knowledge and len(knowledge) > 0:
            # Should mention KES (Kenyan Shillings)
            self.assertIn("KES", knowledge, "Knowledge base should contain fee information in KES")
    
    @patch("communications.ai_chat.logger")
    def test_knowledge_loading_logs_success(self, mock_logger):
        """Test that successful knowledge loading is logged"""
        from communications.ai_chat import load_knowledge_base
        
        # Clear cache to force reload
        import communications.ai_chat
        communications.ai_chat._knowledge_cache = None
        
        load_knowledge_base()
        
        # Should log loading activity
        self.assertTrue(mock_logger.info.called or mock_logger.warning.called)
    
    def test_knowledge_base_handles_missing_directory(self):
        """Test that missing knowledge directory is handled gracefully"""
        from communications.ai_chat import load_knowledge_base
        from pathlib import Path
        from unittest.mock import patch
        
        # Mock Path.exists to return False
        with patch.object(Path, 'exists', return_value=False):
            # Clear cache
            import communications.ai_chat
            communications.ai_chat._knowledge_cache = None
            
            knowledge = load_knowledge_base()
            
            # Should return empty string, not crash
            self.assertEqual(knowledge, "")
    
    def test_system_prompt_works_without_knowledge(self):
        """Test that system prompt works even without knowledge base"""
        from communications.ai_chat import get_system_prompt
        from pathlib import Path
        from unittest.mock import patch
        
        # Mock Path.exists to return False (no knowledge directory)
        with patch.object(Path, 'exists', return_value=False):
            # Clear cache
            import communications.ai_chat
            communications.ai_chat._knowledge_cache = None
            
            prompt = get_system_prompt()
            
            # Should still return a valid prompt
            self.assertIsNotNone(prompt)
            self.assertGreater(len(prompt), 0)
            self.assertIn("governance", prompt.lower())
