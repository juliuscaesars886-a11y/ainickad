"""
Memory management helper functions for AI Assistant.

This module provides functions for managing both session memory (in-memory)
and persistent memory (database) for the conversational AI assistant.

Session memory stores recent conversation context within a single chat session.
Persistent memory stores user preferences and learning data across sessions.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# Session Memory (In-Memory Storage)
# ============================================================================

# In-memory storage for session memory
# Structure: {user_id: [{'user': str, 'assistant': str, 'timestamp': str}]}
_session_memory: Dict[int, List[Dict[str, str]]] = {}


def get_session_memory(user_id: int) -> List[Dict[str, str]]:
    """
    Retrieve session memory for a user.
    
    Returns list of message exchanges (max 10) for the given user.
    Each exchange contains 'user', 'assistant', and 'timestamp' fields.
    
    Args:
        user_id: ID of the user
        
    Returns:
        List of message exchanges, empty list if no memory exists
        
    Example:
        >>> memory = get_session_memory(123)
        >>> print(memory)
        [
            {
                'user': 'What are my tasks?',
                'assistant': 'You have 5 tasks assigned...',
                'timestamp': '2024-01-15T10:30:00'
            }
        ]
    """
    return _session_memory.get(user_id, [])


def update_session_memory(
    user_id: int,
    user_message: str,
    assistant_response: str
) -> None:
    """
    Update session memory with new message exchange.
    
    Maintains max 10 exchanges per user. Older exchanges are automatically
    removed when the limit is exceeded.
    
    Args:
        user_id: ID of the user
        user_message: The user's message
        assistant_response: The assistant's response
        
    Example:
        >>> update_session_memory(123, "Hello", "Hi! How can I help?")
    """
    if user_id not in _session_memory:
        _session_memory[user_id] = []
    
    _session_memory[user_id].append({
        'user': user_message,
        'assistant': assistant_response,
        'timestamp': datetime.now().isoformat()
    })
    
    # Keep only last 10 exchanges
    if len(_session_memory[user_id]) > 10:
        _session_memory[user_id] = _session_memory[user_id][-10:]


def clear_session_memory(user_id: int) -> None:
    """
    Clear session memory for a user.
    
    Removes all stored message exchanges for the given user.
    Called when a chat session ends.
    
    Args:
        user_id: ID of the user
        
    Example:
        >>> clear_session_memory(123)
    """
    if user_id in _session_memory:
        del _session_memory[user_id]


# ============================================================================
# Persistent Memory (Database Storage)
# ============================================================================

def get_user_memory(user_id: int):
    """
    Retrieve or create AssistantMemory for a user.
    
    Creates new record if none exists. Returns None on error.
    
    Args:
        user_id: ID of the user
        
    Returns:
        AssistantMemory instance or None on error
        
    Example:
        >>> memory = get_user_memory(123)
        >>> if memory:
        ...     print(memory.preferred_name)
    """
    try:
        from authentication.models import UserProfile
        from communications.models import AssistantMemory
        
        user = UserProfile.objects.get(id=user_id)
        memory, created = AssistantMemory.objects.get_or_create(user=user)
        
        if created:
            logger.info(f"Created new AssistantMemory for user {user_id}")
        
        return memory
    except UserProfile.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return None
    except Exception as e:
        logger.error(f"Error retrieving user memory for user {user_id}: {e}")
        return None


def update_user_memory(
    user_id: int,
    preferred_name: Optional[str] = None,
    tone_preference: Optional[str] = None,
    role_context: Optional[str] = None
) -> bool:
    """
    Update specific fields in AssistantMemory.
    
    Only updates provided fields, leaving others unchanged.
    
    Args:
        user_id: ID of the user
        preferred_name: User's preferred name (optional)
        tone_preference: Conversational tone preference (optional)
        role_context: Context about user's role (optional)
        
    Returns:
        True if update successful, False otherwise
        
    Example:
        >>> success = update_user_memory(123, preferred_name="Sarah")
        >>> if success:
        ...     print("Memory updated")
    """
    try:
        memory = get_user_memory(user_id)
        if not memory:
            return False
        
        # Update only provided fields
        if preferred_name is not None:
            memory.preferred_name = preferred_name
        if tone_preference is not None:
            memory.tone_preference = tone_preference
        if role_context is not None:
            memory.role_context = role_context
        
        memory.save()
        logger.info(f"Updated user memory for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error updating user memory for user {user_id}: {e}")
        return False


def store_conversation_topic(user_id: int, topic: str) -> bool:
    """
    Add topic to user's last_topics list.
    
    Maintains max 10 topics. Older topics are automatically removed
    when the limit is exceeded.
    
    Args:
        user_id: ID of the user
        topic: Topic to store
        
    Returns:
        True if storage successful, False otherwise
        
    Example:
        >>> success = store_conversation_topic(123, "staff information")
        >>> if success:
        ...     print("Topic stored")
    """
    try:
        memory = get_user_memory(user_id)
        if not memory:
            return False
        
        # Get existing topics or initialize empty list
        topics = memory.last_topics or []
        
        # Add new topic
        topics.append(topic)
        
        # Keep only last 10 topics
        memory.last_topics = topics[-10:]
        memory.save()
        
        logger.info(f"Stored conversation topic '{topic}' for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error storing conversation topic for user {user_id}: {e}")
        return False
