"""
AI Message Classification System

Intelligent message routing and categorization engine that replaces brittle keyword matching
with a sophisticated hybrid classification approach. Analyzes every user message, assigns it
to one of six classification types, and routes it to specialized handlers with confidence
scoring and fallback mechanisms.

Classification Types:
- Navigation: "How do I...", "Where is..." - Help finding features
- Feature_Guide: "What does X do?" - Feature explanations
- Company_Data: "My deadline", "Our board" - Company-specific information
- Kenya_Governance: CMA, Companies Act, BRS questions - Compliance and regulations
- Web_Search: Outside domain questions - External knowledge
- Tip: Ambiguous messages - Clarification requests
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from enum import Enum
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class ClassificationType(Enum):
    """Enumeration of all classification types."""
    NAVIGATION = "Navigation"
    FEATURE_GUIDE = "Feature_Guide"
    COMPANY_DATA = "Company_Data"
    KENYA_GOVERNANCE = "Kenya_Governance"
    WEB_SEARCH = "Web_Search"
    TIP = "Tip"


# Constant for all classification types
CLASSIFICATION_TYPES = [
    ClassificationType.NAVIGATION.value,
    ClassificationType.FEATURE_GUIDE.value,
    ClassificationType.COMPANY_DATA.value,
    ClassificationType.KENYA_GOVERNANCE.value,
    ClassificationType.WEB_SEARCH.value,
    ClassificationType.TIP.value,
]

# Response labels for each classification type
RESPONSE_LABELS = {
    ClassificationType.NAVIGATION.value: "→",
    ClassificationType.FEATURE_GUIDE.value: "?",
    ClassificationType.COMPANY_DATA.value: "◈",
    ClassificationType.KENYA_GOVERNANCE.value: "⚖",
    ClassificationType.WEB_SEARCH.value: "⊕",
    ClassificationType.TIP.value: "!",
}

# Priority order for routing (higher priority = checked first)
PRIORITY_ORDER = [
    (ClassificationType.COMPANY_DATA.value, 0.7),
    (ClassificationType.KENYA_GOVERNANCE.value, 0.75),
    (ClassificationType.FEATURE_GUIDE.value, 0.6),
    (ClassificationType.NAVIGATION.value, 0.6),
    (ClassificationType.WEB_SEARCH.value, 0.5),
    (ClassificationType.TIP.value, 0.0),
]

# Fallback threshold - if all types below this, use fallback
FALLBACK_THRESHOLD = 0.55  # Slightly lower to catch more ambiguous messages

# Representative text samples for semantic similarity (TF-IDF)
SEMANTIC_SAMPLES = {
    ClassificationType.NAVIGATION.value: [
        "How do I create a new company?",
        "Where is the staff management section?",
        "How to upload documents to the system?",
        "Where can I find the dashboard?",
        "How do I navigate to the compliance section?",
        "Where is the reporting feature?",
        "How to access my company profile?",
        "Where can I view pending actions?",
        "How do I find the user management page?",
        "Where is the settings menu?",
        "How to locate the document upload area?",
        "Where can I see my company's health score?",
        "How do I access the board meeting section?",
        "Where is the annual return filing page?",
        "How to find the compliance checklist?",
    ],
    ClassificationType.FEATURE_GUIDE.value: [
        "What does the compliance score feature do?",
        "How does the document management system work?",
        "What is the purpose of the health score?",
        "How does the annual return filing process work?",
        "What are the features of the board meeting module?",
        "How does the user role system work?",
        "What is the purpose of pending actions?",
        "How does the notification system function?",
        "What are the capabilities of the reporting tool?",
        "How does the document versioning work?",
        "What is the purpose of the compliance checklist?",
        "How does the deadline tracking feature work?",
        "What are the features of the director management system?",
        "How does the shareholder registry work?",
        "What is the purpose of the beneficial ownership module?",
    ],
    ClassificationType.COMPANY_DATA.value: [
        "What is my company's compliance score?",
        "Who are the directors of my company?",
        "What are the pending actions for our company?",
        "What is our company's health score?",
        "When is our next annual return deadline?",
        "What documents have we uploaded?",
        "Who are the shareholders in our company?",
        "What is our company's registration number?",
        "What is the beneficial ownership structure?",
        "What are the upcoming compliance deadlines?",
        "How many staff members does our company have?",
        "What is our company's tax ID?",
        "What board meetings are scheduled?",
        "What is our company's current status?",
        "What documents are pending review?",
    ],
    ClassificationType.KENYA_GOVERNANCE.value: [
        "What are the CMA requirements for annual returns?",
        "What does the Companies Act say about director disclosure?",
        "What is the BRS filing deadline?",
        "What are the NSE listing requirements?",
        "What are the KRA tax compliance requirements?",
        "What is the process for beneficial ownership disclosure?",
        "What are the penalties for late filing?",
        "What is the CR12 form used for?",
        "What are the requirements for AGM meetings?",
        "What is the process for director appointment?",
        "What are the shareholder disclosure requirements?",
        "What is the process for company registration?",
        "What are the compliance requirements for listed companies?",
        "What is the process for annual return filing?",
        "What are the governance requirements for board meetings?",
    ],
    ClassificationType.WEB_SEARCH.value: [
        "What is the capital of Kenya?",
        "Who is the current president of Kenya?",
        "What is the weather like in Nairobi?",
        "What are the latest news headlines?",
        "How does cryptocurrency work?",
        "What is the history of the stock market?",
        "What are the best practices for project management?",
        "How do I learn Python programming?",
        "What is artificial intelligence?",
        "What are the benefits of cloud computing?",
        "How does machine learning work?",
        "What is the process for starting a business?",
        "What are the tax implications of freelancing?",
        "How do I improve my credit score?",
        "What are the latest technology trends?",
    ],
    ClassificationType.TIP.value: [
        "I'm not sure what I need",
        "Can you help me?",
        "I'm confused about something",
        "I don't understand this",
        "What should I do?",
        "I'm lost",
        "Can you clarify?",
        "I need help",
        "What does this mean?",
        "I'm not sure",
        "Can you explain?",
        "I don't know where to start",
        "What is this for?",
        "I'm having trouble",
        "Can you assist me?",
    ],
}


@dataclass
class Keyword:
    """Represents a keyword or phrase for classification."""
    text: str  # The keyword or phrase
    weight: float = 1.0  # 0.0-1.0, affects confidence calculation
    regex: bool = False  # If True, treat as regex pattern
    
    def matches(self, message: str) -> bool:
        """Check if keyword matches in message."""
        if self.regex:
            import re
            try:
                return bool(re.search(self.text, message))
            except Exception as e:
                logger.warning(f"Regex match error for '{self.text}': {e}")
                return False
        return self.text in message


@dataclass
class ClassificationResult:
    """Result of message classification."""
    type: str  # One of CLASSIFICATION_TYPES
    confidence: float  # 0.0-1.0
    scores: Dict[str, float]  # Confidence for each type
    label: str  # Visual indicator (→, ?, ◈, ⚖, ⊕, !)
    handler: Optional[Callable] = None  # Function to invoke
    reasoning: str = ""  # Why this classification was chosen
    
    def __post_init__(self):
        """Validate classification result."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")
        
        if self.type not in CLASSIFICATION_TYPES:
            raise ValueError(f"Invalid classification type: {self.type}")
        
        if self.label not in RESPONSE_LABELS.values():
            raise ValueError(f"Invalid response label: {self.label}")


@dataclass
class ClassificationContext:
    """Context information for classification."""
    user_id: Optional[int] = None
    user_role: Optional[str] = None
    company_name: Optional[str] = None
    company_id: Optional[int] = None
    conversation_history: List[str] = field(default_factory=list)
    
    def get_last_messages(self, n: int = 3) -> List[str]:
        """Get last n messages from conversation history."""
        return self.conversation_history[-n:] if self.conversation_history else []


class MessageClassifier:
    """
    Main message classification engine.
    
    Analyzes user messages and assigns classification types with confidence scores.
    Uses hybrid approach: keyword matching (70% weight) + semantic analysis (30% weight).
    """
    
    def __init__(self):
        """Initialize classifier."""
        self.keyword_dictionaries = {}
        self.semantic_models = {}
        self._initialized = False
        self._tfidf_vectorizers = {}
        self._initialize_tfidf_vectorizers()
    
    def classify(
        self,
        message: str,
        context: Optional[ClassificationContext] = None
    ) -> ClassificationResult:
        """
        Classify a user message into one of six types.
        
        Args:
            message: The user's question (will be normalized to lowercase)
            context: Optional context with user role, company data, conversation history
        
        Returns:
            ClassificationResult with type, confidence, label, and handler
        
        Raises:
            ValueError: If message is empty or invalid
        """
        if not message or not isinstance(message, str):
            raise ValueError("Message must be a non-empty string")
        
        try:
            # Normalize message
            normalized_message = self._normalize_message(message)
            
            # Calculate keyword confidence for each type
            keyword_scores = self._calculate_keyword_confidence(normalized_message)
            
            # Calculate semantic confidence for each type (if available)
            semantic_scores = self._calculate_semantic_confidence(normalized_message)
            
            # Combine scores
            final_scores = self._combine_scores(keyword_scores, semantic_scores)
            
            # Apply context boosts
            if context:
                final_scores = self._apply_context_boosts(final_scores, normalized_message, context)
            
            # Select best classification
            best_type = max(final_scores, key=final_scores.get)
            best_confidence = final_scores[best_type]
            
            # Get label and handler
            label = RESPONSE_LABELS.get(best_type, "!")
            handler = self._get_handler(best_type)
            
            # Create result
            result = ClassificationResult(
                type=best_type,
                confidence=best_confidence,
                scores=final_scores,
                label=label,
                handler=handler,
                reasoning=f"Classified as {best_type} with {best_confidence:.2f} confidence"
            )
            
            logger.debug(f"Classification: {result.type} ({result.confidence:.2f}) for: {message[:50]}")
            return result
            
        except Exception as e:
            logger.error(f"Classification error: {e}", exc_info=True)
            # Return default classification (Tip) on error
            return ClassificationResult(
                type=ClassificationType.TIP.value,
                confidence=0.0,
                scores={t: 0.0 for t in CLASSIFICATION_TYPES},
                label=RESPONSE_LABELS[ClassificationType.TIP.value],
                handler=None,
                reasoning=f"Classification error: {str(e)}"
            )
    
    def _normalize_message(self, message: str) -> str:
        """Normalize message to lowercase."""
        return message.lower().strip()
    
    def _initialize_tfidf_vectorizers(self) -> None:
        """
        Initialize TF-IDF vectorizers for each classification type.
        
        Creates a TF-IDF vectorizer for each classification type using representative
        text samples. Vectorizers are cached in memory for performance.
        """
        try:
            for classification_type, samples in SEMANTIC_SAMPLES.items():
                if not samples:
                    logger.warning(f"No semantic samples for {classification_type}")
                    continue
                
                try:
                    # Create TF-IDF vectorizer for this classification type
                    # Use lowercase, remove common English stopwords, and limit to 1-2 word phrases
                    vectorizer = TfidfVectorizer(
                        lowercase=True,
                        stop_words='english',
                        ngram_range=(1, 2),
                        max_features=100,
                        min_df=1,
                        max_df=1.0,
                    )
                    
                    # Fit the vectorizer on the representative samples
                    vectorizer.fit(samples)
                    
                    # Cache the vectorizer
                    self._tfidf_vectorizers[classification_type] = vectorizer
                    
                    logger.debug(
                        f"Initialized TF-IDF vectorizer for {classification_type} "
                        f"with {len(samples)} samples"
                    )
                    
                except Exception as e:
                    logger.error(
                        f"Error initializing TF-IDF vectorizer for {classification_type}: {e}",
                        exc_info=True
                    )
            
            logger.info(
                f"TF-IDF vectorizers initialized for {len(self._tfidf_vectorizers)} "
                f"classification types"
            )
            
        except Exception as e:
            logger.error(f"Error initializing TF-IDF vectorizers: {e}", exc_info=True)
    
    def _calculate_keyword_confidence(self, message: str) -> Dict[str, float]:
        """
        Calculate keyword-based confidence for each classification type.
        
        Returns:
            Dict mapping classification type to confidence score (0.0-1.0)
        """
        scores = {t: 0.0 for t in CLASSIFICATION_TYPES}
        
        try:
            if not self.keyword_dictionaries:
                logger.warning("Keyword dictionaries not loaded")
                return scores
            
            for classification_type, keywords in self.keyword_dictionaries.items():
                if classification_type not in scores:
                    continue
                
                max_weight = 0.0
                for keyword in keywords:
                    if keyword.matches(message):
                        max_weight = max(max_weight, keyword.weight)
                
                scores[classification_type] = min(max_weight, 1.0)
            
            return scores
            
        except Exception as e:
            logger.error(f"Keyword confidence calculation error: {e}", exc_info=True)
            return scores
    
    def _calculate_semantic_confidence(self, message: str) -> Dict[str, float]:
        """
        Calculate semantic similarity confidence for each classification type.
        
        Uses TF-IDF vectorization and cosine similarity to measure semantic similarity
        between the user message and representative samples for each classification type.
        
        Returns:
            Dict mapping classification type to confidence score (0.0-1.0)
        """
        scores = {t: 0.0 for t in CLASSIFICATION_TYPES}
        
        try:
            if not self._tfidf_vectorizers:
                logger.warning("TF-IDF vectorizers not initialized")
                return scores
            
            for classification_type, vectorizer in self._tfidf_vectorizers.items():
                if classification_type not in scores:
                    continue
                
                try:
                    # Vectorize the user message
                    message_vector = vectorizer.transform([message])
                    
                    # Get the representative samples for this type
                    samples = SEMANTIC_SAMPLES.get(classification_type, [])
                    if not samples:
                        continue
                    
                    # Vectorize the samples
                    samples_vector = vectorizer.transform(samples)
                    
                    # Calculate cosine similarity between message and all samples
                    similarities = cosine_similarity(message_vector, samples_vector)
                    
                    # Take the maximum similarity as the confidence score
                    # This represents how similar the message is to the best-matching sample
                    max_similarity = float(np.max(similarities)) if similarities.size > 0 else 0.0
                    
                    # Ensure score is between 0.0 and 1.0
                    scores[classification_type] = min(max(max_similarity, 0.0), 1.0)
                    
                except Exception as e:
                    logger.warning(
                        f"Semantic similarity calculation error for {classification_type}: {e}"
                    )
                    scores[classification_type] = 0.0
            
            return scores
            
        except Exception as e:
            logger.error(f"Semantic confidence calculation error: {e}", exc_info=True)
            return scores
    
    def _combine_scores(
        self,
        keyword_scores: Dict[str, float],
        semantic_scores: Dict[str, float],
        keyword_weight: float = 0.8,
        semantic_weight: float = 0.2
    ) -> Dict[str, float]:
        """
        Combine keyword and semantic confidence scores.
        
        Formula: final_confidence = (keyword_confidence × 0.8) + (semantic_confidence × 0.2)
        
        Args:
            keyword_scores: Keyword-based confidence for each type
            semantic_scores: Semantic-based confidence for each type
            keyword_weight: Weight for keyword scores (default 0.8)
            semantic_weight: Weight for semantic scores (default 0.2)
        
        Returns:
            Combined confidence scores for each type
        """
        combined = {}
        for classification_type in CLASSIFICATION_TYPES:
            kw_score = keyword_scores.get(classification_type, 0.0)
            sem_score = semantic_scores.get(classification_type, 0.0)
            
            combined_score = (kw_score * keyword_weight) + (sem_score * semantic_weight)
            combined[classification_type] = min(combined_score, 1.0)
        
        return combined
    
    def _apply_context_boosts(
        self,
        scores: Dict[str, float],
        message: str,
        context: ClassificationContext
    ) -> Dict[str, float]:
        """
        Apply context-based confidence boosts.
        
        Boosts:
        - Company_Data: +0.2 if message contains "my company" or "our directors"
        - Feature_Guide: +0.15 if user is Admin and message mentions "users" or "permissions"
        - Kenya_Governance: +0.25 if message contains "BRS" or "CMA"
        
        Args:
            scores: Current confidence scores
            message: Normalized user message
            context: Classification context with user role and company data
        
        Returns:
            Adjusted confidence scores (capped at 1.0)
        """
        boosted = scores.copy()
        
        try:
            # Company_Data boost
            if "my company" in message or "our directors" in message or "our board" in message:
                boosted[ClassificationType.COMPANY_DATA.value] = min(
                    boosted[ClassificationType.COMPANY_DATA.value] + 0.2, 1.0
                )
            
            # Feature_Guide boost for Admin users
            if context.user_role and "admin" in context.user_role.lower():
                if "users" in message or "permissions" in message or "roles" in message:
                    boosted[ClassificationType.FEATURE_GUIDE.value] = min(
                        boosted[ClassificationType.FEATURE_GUIDE.value] + 0.15, 1.0
                    )
            
            # Kenya_Governance boost
            if "brs" in message or "cma" in message or "kra" in message or "nse" in message:
                boosted[ClassificationType.KENYA_GOVERNANCE.value] = min(
                    boosted[ClassificationType.KENYA_GOVERNANCE.value] + 0.25, 1.0
                )
            
            return boosted
            
        except Exception as e:
            logger.error(f"Context boost error: {e}", exc_info=True)
            return scores
    
    def _get_handler(self, classification_type: str) -> Optional[Callable]:
        """Get response handler for classification type."""
        # Handlers will be implemented in Task 1.4
        # For now, return None
        return None
    
    def load_keywords(self, keyword_dictionaries: Dict[str, List[Keyword]]) -> None:
        """
        Load keyword dictionaries for classification.
        
        Args:
            keyword_dictionaries: Dict mapping classification type to list of keywords
        """
        try:
            self.keyword_dictionaries = keyword_dictionaries
            logger.info(f"Loaded keyword dictionaries for {len(keyword_dictionaries)} types")
            self._initialized = True
        except Exception as e:
            logger.error(f"Error loading keyword dictionaries: {e}", exc_info=True)
    
    def is_initialized(self) -> bool:
        """Check if classifier is initialized with keywords."""
        return self._initialized


class RoutingEngine:
    """
    Routes classified messages to appropriate handlers based on priority and confidence.
    
    Priority Order:
    1. Company_Data (confidence > 0.7)
    2. Kenya_Governance (confidence > 0.75)
    3. Feature_Guide (confidence > 0.6)
    4. Navigation (confidence > 0.6)
    5. Web_Search (confidence > 0.5)
    6. Tip (confidence > 0.0)
    """
    
    def __init__(self):
        """Initialize routing engine."""
        self.handlers = {}
        self.priority_order = PRIORITY_ORDER
    
    def route(
        self,
        classification: ClassificationResult,
        user_message: str,
        context: Optional[ClassificationContext] = None,
        user=None
    ) -> str:
        """
        Route classified message to appropriate handler and return response.
        
        Args:
            classification: Classification result from classifier
            user_message: Original user message
            context: Optional classification context
            user: Optional user object (for backward compatibility)
        
        Returns:
            Response string from the handler
        """
        try:
            # Create context from user if not provided
            if context is None and user is not None:
                context = ClassificationContext(
                    user_id=user.id if hasattr(user, 'id') else None,
                    user_role=user.get_role_display() if hasattr(user, 'get_role_display') else None,
                    company_name=user.company.name if hasattr(user, 'company') and user.company else None,
                    company_id=user.company.id if hasattr(user, 'company') and user.company else None,
                )
            
            # Check priority thresholds
            for type_name, threshold in self.priority_order:
                confidence = classification.scores.get(type_name, 0.0)
                
                if confidence >= threshold:
                    handler = self.handlers.get(type_name)
                    logger.debug(
                        f"Routing to {type_name} handler (confidence: {confidence:.2f}, "
                        f"threshold: {threshold})"
                    )
                    if handler:
                        return handler(user_message, classification, context)
                    else:
                        logger.warning(f"No handler registered for {type_name}")
                        # Fall through to fallback
            
            # Fallback to Tip handler if no threshold met
            logger.debug("No priority threshold met, routing to Tip handler")
            fallback_handler = self.handlers.get(ClassificationType.TIP.value)
            if fallback_handler:
                return fallback_handler(user_message, classification, context)
            else:
                return "I'm not sure how to help with that. Could you rephrase your question?"
            
        except Exception as e:
            logger.error(f"Routing error: {e}", exc_info=True)
            fallback_handler = self.handlers.get(ClassificationType.TIP.value)
            if fallback_handler:
                return fallback_handler(user_message, classification, context)
            else:
                return "I encountered an error processing your request. Please try again."
    
    def register_handler(self, classification_type: str, handler: Callable) -> None:
        """
        Register a response handler for a classification type.
        
        Args:
            classification_type: One of CLASSIFICATION_TYPES
            handler: Callable that generates response for this type
        """
        if classification_type not in CLASSIFICATION_TYPES:
            raise ValueError(f"Invalid classification type: {classification_type}")
        
        self.handlers[classification_type] = handler
        logger.debug(f"Registered handler for {classification_type}")
    
    def get_handler(self, classification_type: str) -> Optional[Callable]:
        """Get handler for classification type."""
        return self.handlers.get(classification_type)


# Global routing engine instance
_routing_engine_instance: Optional[RoutingEngine] = None


def get_routing_engine() -> RoutingEngine:
    """Get or create global routing engine instance."""
    global _routing_engine_instance
    if _routing_engine_instance is None:
        _routing_engine_instance = RoutingEngine()
    return _routing_engine_instance


def reset_routing_engine() -> None:
    """Reset global routing engine instance."""
    global _routing_engine_instance
    _routing_engine_instance = None


# Global classifier instance
_classifier_instance: Optional[MessageClassifier] = None


def get_classifier() -> MessageClassifier:
    """Get or create global classifier instance."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = MessageClassifier()
    return _classifier_instance


def reset_classifier() -> None:
    """Reset global classifier instance."""
    global _classifier_instance
    _classifier_instance = None


def log_classification(
    classification_result: ClassificationResult,
    user_message: str,
    user=None,
    processing_time_ms: float = 0.0,
    context_data: Optional[Dict] = None
) -> None:
    """
    Log a classification result to the database for monitoring and analysis.
    
    Includes automatic warnings for:
    - Performance issues (> 500ms classifications)
    - Low confidence classifications (< 0.6)
    
    Args:
        classification_result: The classification result to log
        user_message: The original user message
        user: Optional user profile
        processing_time_ms: Time taken to classify in milliseconds
        context_data: Optional context data (user role, company, etc.)
    
    Returns:
        None
    
    **Validates: Requirements 10.1, 10.2, 11.3**
    """
    try:
        from communications.models import ClassificationLog
        
        # Prepare context data
        if context_data is None:
            context_data = {}
        
        # Performance warning for slow classifications (> 500ms)
        if processing_time_ms > 500:
            logger.warning(
                f"PERFORMANCE WARNING: Classification took {processing_time_ms:.1f}ms "
                f"(threshold: 500ms) for message: '{user_message[:50]}...' "
                f"[Type: {classification_result.type}, Confidence: {classification_result.confidence:.2f}]"
            )
        
        # Low confidence warning (< 0.6)
        if classification_result.confidence < 0.6:
            logger.warning(
                f"LOW CONFIDENCE WARNING: Classification confidence {classification_result.confidence:.2f} "
                f"(threshold: 0.6) for message: '{user_message[:50]}...' "
                f"[Type: {classification_result.type}, All scores: {classification_result.scores}]"
            )
        
        # Create log entry
        log_entry = ClassificationLog(
            user=user,
            message=user_message,
            classification_type=classification_result.type,
            confidence_score=classification_result.confidence,
            all_scores=classification_result.scores,
            processing_time_ms=int(processing_time_ms),
            context_data=context_data,
            user_feedback='none'  # Default to no feedback
        )
        
        # Save to database
        log_entry.save()
        
        logger.debug(
            f"Classification logged: {classification_result.type} "
            f"({classification_result.confidence:.2f}) - {processing_time_ms:.1f}ms"
        )
        
    except Exception as e:
        logger.error(f"Failed to log classification: {e}", exc_info=True)
        # Don't raise - logging failure should not break classification
