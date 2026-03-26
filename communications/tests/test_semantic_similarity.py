"""
Tests for semantic similarity engine (TF-IDF).

Tests verify that:
1. Semantic confidence is between 0.0 and 1.0
2. Paraphrased messages get reasonable semantic scores
3. Unrelated messages get low semantic scores
4. Vectorizers are properly cached
"""

import pytest
from communications.classifier import (
    MessageClassifier,
    ClassificationContext,
    ClassificationType,
    SEMANTIC_SAMPLES,
)


class TestSemanticSimilarity:
    """Test semantic similarity engine."""
    
    @pytest.fixture
    def classifier(self):
        """Create a fresh classifier instance."""
        return MessageClassifier()
    
    def test_semantic_confidence_in_valid_range(self, classifier):
        """Test that semantic confidence is always between 0.0 and 1.0."""
        test_messages = [
            "How do I create a company?",
            "What does the compliance score do?",
            "My company's deadline",
            "CMA requirements",
            "What is the weather?",
            "I need help",
            "xyz abc def ghi jkl",  # Random words
            "",  # Empty (will be handled by classify)
        ]
        
        for message in test_messages:
            if not message:
                continue
            
            result = classifier.classify(message)
            
            # Check that all semantic scores are in valid range
            for score in result.scores.values():
                assert 0.0 <= score <= 1.0, f"Score {score} out of range for message: {message}"
    
    def test_paraphrased_messages_similar_scores(self, classifier):
        """Test that paraphrased messages get similar semantic scores."""
        # These messages have similar meaning but different wording
        navigation_messages = [
            "How do I create a company?",
            "How can I create a new company?",
            "What is the process to create a company?",
            "Where do I go to create a company?",
        ]
        
        scores_list = []
        for message in navigation_messages:
            result = classifier.classify(message)
            nav_score = result.scores[ClassificationType.NAVIGATION.value]
            scores_list.append(nav_score)
        
        # All scores should be positive (> 0.0) for navigation messages
        for score in scores_list:
            assert score > 0.0, f"Navigation score too low: {score}"
        
        # Scores should be relatively similar (within 0.2 of each other)
        max_score = max(scores_list)
        min_score = min(scores_list)
        assert max_score - min_score < 0.2, f"Scores too different: {scores_list}"
    
    def test_unrelated_messages_low_scores(self, classifier):
        """Test that unrelated messages get low semantic scores."""
        # Navigation message should have low score for Company_Data
        result = classifier.classify("How do I navigate to the dashboard?")
        company_data_score = result.scores[ClassificationType.COMPANY_DATA.value]
        
        # Should be relatively low (< 0.5)
        assert company_data_score < 0.5, f"Company_Data score too high for navigation message: {company_data_score}"
    
    def test_company_data_messages_high_scores(self, classifier):
        """Test that company data messages get high semantic scores."""
        company_data_messages = [
            "What is my company's compliance score?",
            "Who are the directors of my company?",
            "What are the pending actions for our company?",
        ]
        
        for message in company_data_messages:
            result = classifier.classify(message)
            company_data_score = result.scores[ClassificationType.COMPANY_DATA.value]
            
            # Should be positive (> 0.0)
            assert company_data_score > 0.0, f"Company_Data score too low for '{message}': {company_data_score}"
    
    def test_governance_messages_high_scores(self, classifier):
        """Test that governance messages get high semantic scores."""
        governance_messages = [
            "What are the CMA requirements?",
            "What does the Companies Act say?",
            "What is the BRS filing deadline?",
        ]
        
        for message in governance_messages:
            result = classifier.classify(message)
            governance_score = result.scores[ClassificationType.KENYA_GOVERNANCE.value]
            
            # Should be positive (> 0.0)
            assert governance_score > 0.0, f"Governance score too low for '{message}': {governance_score}"
    
    def test_feature_guide_messages_high_scores(self, classifier):
        """Test that feature guide messages get high semantic scores."""
        feature_messages = [
            "What does the compliance score feature do?",
            "How does the document management system work?",
            "What is the purpose of the health score?",
        ]
        
        for message in feature_messages:
            result = classifier.classify(message)
            feature_score = result.scores[ClassificationType.FEATURE_GUIDE.value]
            
            # Should be positive (> 0.0)
            assert feature_score > 0.0, f"Feature_Guide score too low for '{message}': {feature_score}"
    
    def test_web_search_messages_reasonable_scores(self, classifier):
        """Test that web search messages get reasonable semantic scores."""
        web_search_messages = [
            "What is the capital of Kenya?",
            "Who is the current president?",
            "What is artificial intelligence?",
        ]
        
        for message in web_search_messages:
            result = classifier.classify(message)
            web_score = result.scores[ClassificationType.WEB_SEARCH.value]
            
            # Should be in valid range
            assert 0.0 <= web_score <= 1.0, f"Web_Search score out of range for '{message}': {web_score}"
    
    def test_vectorizers_cached(self, classifier):
        """Test that TF-IDF vectorizers are cached in memory."""
        # Check that vectorizers are initialized
        assert len(classifier._tfidf_vectorizers) > 0, "No vectorizers initialized"
        
        # Check that all classification types have vectorizers
        for classification_type in [
            ClassificationType.NAVIGATION.value,
            ClassificationType.FEATURE_GUIDE.value,
            ClassificationType.COMPANY_DATA.value,
            ClassificationType.KENYA_GOVERNANCE.value,
            ClassificationType.WEB_SEARCH.value,
            ClassificationType.TIP.value,
        ]:
            assert classification_type in classifier._tfidf_vectorizers, \
                f"No vectorizer for {classification_type}"
    
    def test_semantic_samples_exist(self):
        """Test that semantic samples are defined for all types."""
        for classification_type in [
            ClassificationType.NAVIGATION.value,
            ClassificationType.FEATURE_GUIDE.value,
            ClassificationType.COMPANY_DATA.value,
            ClassificationType.KENYA_GOVERNANCE.value,
            ClassificationType.WEB_SEARCH.value,
            ClassificationType.TIP.value,
        ]:
            assert classification_type in SEMANTIC_SAMPLES, \
                f"No semantic samples for {classification_type}"
            
            samples = SEMANTIC_SAMPLES[classification_type]
            assert len(samples) >= 10, \
                f"Too few samples for {classification_type}: {len(samples)}"
    
    def test_semantic_confidence_with_context(self, classifier):
        """Test that semantic confidence works with classification context."""
        context = ClassificationContext(
            user_id=1,
            user_role="Admin",
            company_name="Test Company",
            company_id=1,
        )
        
        result = classifier.classify("How do I create a company?", context)
        
        # Should still have valid confidence scores
        assert 0.0 <= result.confidence <= 1.0
        for score in result.scores.values():
            assert 0.0 <= score <= 1.0
    
    def test_semantic_consistency(self, classifier):
        """Test that same message produces consistent semantic scores."""
        message = "How do I create a company?"
        
        # Classify the same message multiple times
        results = [classifier.classify(message) for _ in range(3)]
        
        # All results should have the same scores (within floating point precision)
        first_scores = results[0].scores
        for result in results[1:]:
            for classification_type in first_scores:
                assert abs(first_scores[classification_type] - result.scores[classification_type]) < 0.001, \
                    f"Inconsistent scores for {classification_type}"
    
    def test_short_message_semantic_analysis(self, classifier):
        """Test that semantic analysis works with short messages."""
        short_messages = [
            "How do I?",
            "What is?",
            "Help me",
            "My company",
        ]
        
        for message in short_messages:
            result = classifier.classify(message)
            
            # Should still have valid confidence scores
            assert 0.0 <= result.confidence <= 1.0
            for score in result.scores.values():
                assert 0.0 <= score <= 1.0
    
    def test_long_message_semantic_analysis(self, classifier):
        """Test that semantic analysis works with long messages."""
        long_message = (
            "I would like to know how I can create a new company in the system. "
            "I need to understand the process and what information is required. "
            "Can you guide me through the steps?"
        )
        
        result = classifier.classify(long_message)
        
        # Should still have valid confidence scores
        assert 0.0 <= result.confidence <= 1.0
        for score in result.scores.values():
            assert 0.0 <= score <= 1.0
        
        # Navigation should have positive score
        nav_score = result.scores[ClassificationType.NAVIGATION.value]
        assert nav_score > 0.0, f"Navigation score too low for long message: {nav_score}"
