"""
Tests for confidence combination formula (Property 8).

Tests verify that:
1. Final confidence = (keyword_confidence × 0.7) + (semantic_confidence × 0.3)
2. Final confidence is capped at 1.0
3. Combined scores are returned for all types
4. Formula is applied consistently across all classification types

**Validates: Requirements 7.5**
**Validates: Property 8: Confidence Combination Formula**
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from communications.classifier import (
    MessageClassifier,
    ClassificationContext,
    ClassificationType,
    CLASSIFICATION_TYPES,
)


class TestConfidenceCombinationFormula:
    """Test the confidence combination formula."""
    
    @pytest.fixture
    def classifier(self):
        """Create a fresh classifier instance."""
        return MessageClassifier()
    
    def test_combine_scores_basic_formula(self, classifier):
        """Test that _combine_scores applies the correct formula."""
        # Test with known values
        keyword_scores = {
            ClassificationType.NAVIGATION.value: 0.8,
            ClassificationType.FEATURE_GUIDE.value: 0.5,
            ClassificationType.COMPANY_DATA.value: 0.3,
            ClassificationType.KENYA_GOVERNANCE.value: 0.2,
            ClassificationType.WEB_SEARCH.value: 0.1,
            ClassificationType.TIP.value: 0.0,
        }
        
        semantic_scores = {
            ClassificationType.NAVIGATION.value: 0.6,
            ClassificationType.FEATURE_GUIDE.value: 0.7,
            ClassificationType.COMPANY_DATA.value: 0.9,
            ClassificationType.KENYA_GOVERNANCE.value: 0.4,
            ClassificationType.WEB_SEARCH.value: 0.8,
            ClassificationType.TIP.value: 0.5,
        }
        
        combined = classifier._combine_scores(keyword_scores, semantic_scores)
        
        # Verify formula: final = (keyword × 0.7) + (semantic × 0.3)
        expected = {
            ClassificationType.NAVIGATION.value: (0.8 * 0.7) + (0.6 * 0.3),  # 0.56 + 0.18 = 0.74
            ClassificationType.FEATURE_GUIDE.value: (0.5 * 0.7) + (0.7 * 0.3),  # 0.35 + 0.21 = 0.56
            ClassificationType.COMPANY_DATA.value: (0.3 * 0.7) + (0.9 * 0.3),  # 0.21 + 0.27 = 0.48
            ClassificationType.KENYA_GOVERNANCE.value: (0.2 * 0.7) + (0.4 * 0.3),  # 0.14 + 0.12 = 0.26
            ClassificationType.WEB_SEARCH.value: (0.1 * 0.7) + (0.8 * 0.3),  # 0.07 + 0.24 = 0.31
            ClassificationType.TIP.value: (0.0 * 0.7) + (0.5 * 0.3),  # 0.0 + 0.15 = 0.15
        }
        
        for classification_type in CLASSIFICATION_TYPES:
            assert abs(combined[classification_type] - expected[classification_type]) < 0.001, \
                f"Formula incorrect for {classification_type}: got {combined[classification_type]}, expected {expected[classification_type]}"
    
    def test_combine_scores_capped_at_one(self, classifier):
        """Test that combined scores are capped at 1.0."""
        # Create scores that would exceed 1.0 if not capped
        keyword_scores = {
            ClassificationType.NAVIGATION.value: 1.0,
            ClassificationType.FEATURE_GUIDE.value: 1.0,
            ClassificationType.COMPANY_DATA.value: 0.9,
            ClassificationType.KENYA_GOVERNANCE.value: 0.8,
            ClassificationType.WEB_SEARCH.value: 0.7,
            ClassificationType.TIP.value: 0.6,
        }
        
        semantic_scores = {
            ClassificationType.NAVIGATION.value: 1.0,  # Would be 1.0 * 0.7 + 1.0 * 0.3 = 1.0
            ClassificationType.FEATURE_GUIDE.value: 0.9,  # Would be 1.0 * 0.7 + 0.9 * 0.3 = 0.97
            ClassificationType.COMPANY_DATA.value: 1.0,  # Would be 0.9 * 0.7 + 1.0 * 0.3 = 0.93
            ClassificationType.KENYA_GOVERNANCE.value: 1.0,  # Would be 0.8 * 0.7 + 1.0 * 0.3 = 0.86
            ClassificationType.WEB_SEARCH.value: 1.0,  # Would be 0.7 * 0.7 + 1.0 * 0.3 = 0.79
            ClassificationType.TIP.value: 1.0,  # Would be 0.6 * 0.7 + 1.0 * 0.3 = 0.72
        }
        
        combined = classifier._combine_scores(keyword_scores, semantic_scores)
        
        # All scores should be <= 1.0
        for classification_type in CLASSIFICATION_TYPES:
            assert combined[classification_type] <= 1.0, \
                f"Score not capped for {classification_type}: {combined[classification_type]}"
    
    def test_combine_scores_returns_all_types(self, classifier):
        """Test that combined scores are returned for all types."""
        keyword_scores = {t: 0.5 for t in CLASSIFICATION_TYPES}
        semantic_scores = {t: 0.5 for t in CLASSIFICATION_TYPES}
        
        combined = classifier._combine_scores(keyword_scores, semantic_scores)
        
        # Should have scores for all types
        assert len(combined) == len(CLASSIFICATION_TYPES), \
            f"Expected {len(CLASSIFICATION_TYPES)} types, got {len(combined)}"
        
        for classification_type in CLASSIFICATION_TYPES:
            assert classification_type in combined, \
                f"Missing score for {classification_type}"
    
    def test_combine_scores_zero_scores(self, classifier):
        """Test that combining zero scores produces zero."""
        keyword_scores = {t: 0.0 for t in CLASSIFICATION_TYPES}
        semantic_scores = {t: 0.0 for t in CLASSIFICATION_TYPES}
        
        combined = classifier._combine_scores(keyword_scores, semantic_scores)
        
        for classification_type in CLASSIFICATION_TYPES:
            assert combined[classification_type] == 0.0, \
                f"Expected 0.0 for {classification_type}, got {combined[classification_type]}"
    
    def test_combine_scores_keyword_dominant(self, classifier):
        """Test that keyword scores have more weight (0.7) than semantic (0.3)."""
        # High keyword, low semantic
        keyword_scores = {
            ClassificationType.NAVIGATION.value: 1.0,
            ClassificationType.FEATURE_GUIDE.value: 0.0,
            ClassificationType.COMPANY_DATA.value: 0.0,
            ClassificationType.KENYA_GOVERNANCE.value: 0.0,
            ClassificationType.WEB_SEARCH.value: 0.0,
            ClassificationType.TIP.value: 0.0,
        }
        
        semantic_scores = {
            ClassificationType.NAVIGATION.value: 0.0,
            ClassificationType.FEATURE_GUIDE.value: 1.0,
            ClassificationType.COMPANY_DATA.value: 1.0,
            ClassificationType.KENYA_GOVERNANCE.value: 1.0,
            ClassificationType.WEB_SEARCH.value: 1.0,
            ClassificationType.TIP.value: 1.0,
        }
        
        combined = classifier._combine_scores(keyword_scores, semantic_scores)
        
        # Navigation should be highest (1.0 * 0.7 + 0.0 * 0.3 = 0.7)
        nav_score = combined[ClassificationType.NAVIGATION.value]
        assert nav_score == 0.7, f"Navigation score should be 0.7, got {nav_score}"
        
        # Feature_Guide should be lower (0.0 * 0.7 + 1.0 * 0.3 = 0.3)
        feature_score = combined[ClassificationType.FEATURE_GUIDE.value]
        assert feature_score == 0.3, f"Feature_Guide score should be 0.3, got {feature_score}"
        
        # Navigation should be higher than Feature_Guide
        assert nav_score > feature_score, \
            f"Keyword weight not dominant: {nav_score} should be > {feature_score}"
    
    def test_combine_scores_semantic_fallback(self, classifier):
        """Test that semantic scores contribute when keyword scores are low."""
        # Low keyword, high semantic
        keyword_scores = {
            ClassificationType.NAVIGATION.value: 0.1,
            ClassificationType.FEATURE_GUIDE.value: 0.0,
            ClassificationType.COMPANY_DATA.value: 0.0,
            ClassificationType.KENYA_GOVERNANCE.value: 0.0,
            ClassificationType.WEB_SEARCH.value: 0.0,
            ClassificationType.TIP.value: 0.0,
        }
        
        semantic_scores = {
            ClassificationType.NAVIGATION.value: 0.9,
            ClassificationType.FEATURE_GUIDE.value: 0.0,
            ClassificationType.COMPANY_DATA.value: 0.0,
            ClassificationType.KENYA_GOVERNANCE.value: 0.0,
            ClassificationType.WEB_SEARCH.value: 0.0,
            ClassificationType.TIP.value: 0.0,
        }
        
        combined = classifier._combine_scores(keyword_scores, semantic_scores)
        
        # Navigation should be (0.1 * 0.7) + (0.9 * 0.3) = 0.07 + 0.27 = 0.34
        nav_score = combined[ClassificationType.NAVIGATION.value]
        expected = (0.1 * 0.7) + (0.9 * 0.3)
        assert abs(nav_score - expected) < 0.001, \
            f"Navigation score should be {expected}, got {nav_score}"
    
    def test_combine_scores_weights_sum_to_one(self, classifier):
        """Test that keyword and semantic weights sum to 1.0."""
        # When both scores are equal, result should be the same
        keyword_scores = {t: 0.5 for t in CLASSIFICATION_TYPES}
        semantic_scores = {t: 0.5 for t in CLASSIFICATION_TYPES}
        
        combined = classifier._combine_scores(keyword_scores, semantic_scores)
        
        for classification_type in CLASSIFICATION_TYPES:
            # (0.5 * 0.7) + (0.5 * 0.3) = 0.35 + 0.15 = 0.5
            assert abs(combined[classification_type] - 0.5) < 0.001, \
                f"Expected 0.5 for {classification_type}, got {combined[classification_type]}"
    
    def test_combine_scores_custom_weights(self, classifier):
        """Test that custom weights can be passed to _combine_scores."""
        keyword_scores = {t: 0.8 for t in CLASSIFICATION_TYPES}
        semantic_scores = {t: 0.2 for t in CLASSIFICATION_TYPES}
        
        # Test with custom weights (0.5 keyword, 0.5 semantic)
        combined = classifier._combine_scores(
            keyword_scores,
            semantic_scores,
            keyword_weight=0.5,
            semantic_weight=0.5
        )
        
        for classification_type in CLASSIFICATION_TYPES:
            # (0.8 * 0.5) + (0.2 * 0.5) = 0.4 + 0.1 = 0.5
            expected = (0.8 * 0.5) + (0.2 * 0.5)
            assert abs(combined[classification_type] - expected) < 0.001, \
                f"Expected {expected} for {classification_type}, got {combined[classification_type]}"
    
    def test_combine_scores_missing_types_default_to_zero(self, classifier):
        """Test that missing types default to 0.0 in scoring."""
        # Only provide some types
        keyword_scores = {
            ClassificationType.NAVIGATION.value: 0.8,
            ClassificationType.FEATURE_GUIDE.value: 0.6,
        }
        
        semantic_scores = {
            ClassificationType.COMPANY_DATA.value: 0.7,
            ClassificationType.KENYA_GOVERNANCE.value: 0.5,
        }
        
        combined = classifier._combine_scores(keyword_scores, semantic_scores)
        
        # Navigation: (0.8 * 0.7) + (0.0 * 0.3) = 0.56
        nav_score = combined[ClassificationType.NAVIGATION.value]
        assert abs(nav_score - 0.56) < 0.001, f"Navigation score incorrect: {nav_score}"
        
        # Company_Data: (0.0 * 0.7) + (0.7 * 0.3) = 0.21
        company_score = combined[ClassificationType.COMPANY_DATA.value]
        assert abs(company_score - 0.21) < 0.001, f"Company_Data score incorrect: {company_score}"
    
    @given(
        keyword_score=st.floats(min_value=0.0, max_value=1.0),
        semantic_score=st.floats(min_value=0.0, max_value=1.0),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_combine_scores_formula_property(self, classifier, keyword_score, semantic_score):
        """
        Property test: For any keyword and semantic scores, the combined score
        SHALL equal (keyword × 0.7) + (semantic × 0.3), capped at 1.0.
        
        **Validates: Property 8: Confidence Combination Formula**
        """
        keyword_scores = {t: keyword_score for t in CLASSIFICATION_TYPES}
        semantic_scores = {t: semantic_score for t in CLASSIFICATION_TYPES}
        
        combined = classifier._combine_scores(keyword_scores, semantic_scores)
        
        # Calculate expected value
        expected = (keyword_score * 0.7) + (semantic_score * 0.3)
        expected = min(expected, 1.0)  # Cap at 1.0
        
        for classification_type in CLASSIFICATION_TYPES:
            assert abs(combined[classification_type] - expected) < 0.001, \
                f"Formula failed for {classification_type}: keyword={keyword_score}, semantic={semantic_score}"
    
    @given(
        keyword_score=st.floats(min_value=0.0, max_value=1.0),
        semantic_score=st.floats(min_value=0.0, max_value=1.0),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_combine_scores_always_in_range(self, classifier, keyword_score, semantic_score):
        """
        Property test: For any keyword and semantic scores, the combined score
        SHALL always be between 0.0 and 1.0.
        """
        keyword_scores = {t: keyword_score for t in CLASSIFICATION_TYPES}
        semantic_scores = {t: semantic_score for t in CLASSIFICATION_TYPES}
        
        combined = classifier._combine_scores(keyword_scores, semantic_scores)
        
        for classification_type in CLASSIFICATION_TYPES:
            assert 0.0 <= combined[classification_type] <= 1.0, \
                f"Score out of range for {classification_type}: {combined[classification_type]}"
    
    def test_combine_scores_integration_with_classify(self, classifier):
        """Test that _combine_scores is properly integrated in classify method."""
        # Classify a message and verify the formula is applied
        result = classifier.classify("How do I create a company?")
        
        # All scores should be in valid range
        for score in result.scores.values():
            assert 0.0 <= score <= 1.0, f"Score out of range: {score}"
        
        # Final confidence should be in valid range
        assert 0.0 <= result.confidence <= 1.0, f"Confidence out of range: {result.confidence}"
        
        # Final confidence should match the highest score
        max_score = max(result.scores.values())
        assert abs(result.confidence - max_score) < 0.001, \
            f"Confidence {result.confidence} doesn't match max score {max_score}"
    
    def test_combine_scores_multiple_messages(self, classifier):
        """Test that combine_scores works correctly across multiple messages."""
        test_messages = [
            "How do I create a company?",
            "What does the compliance score do?",
            "My company's deadline",
            "CMA requirements",
            "What is the weather?",
        ]
        
        for message in test_messages:
            result = classifier.classify(message)
            
            # All scores should be in valid range
            for score in result.scores.values():
                assert 0.0 <= score <= 1.0, f"Score out of range for '{message}': {score}"
            
            # Final confidence should match max score
            max_score = max(result.scores.values())
            assert abs(result.confidence - max_score) < 0.001, \
                f"Confidence mismatch for '{message}': {result.confidence} vs {max_score}"
    
    def test_combine_scores_edge_case_all_zero(self, classifier):
        """Test edge case where all scores are zero."""
        keyword_scores = {t: 0.0 for t in CLASSIFICATION_TYPES}
        semantic_scores = {t: 0.0 for t in CLASSIFICATION_TYPES}
        
        combined = classifier._combine_scores(keyword_scores, semantic_scores)
        
        for classification_type in CLASSIFICATION_TYPES:
            assert combined[classification_type] == 0.0, \
                f"Expected 0.0 for {classification_type}, got {combined[classification_type]}"
    
    def test_combine_scores_edge_case_all_one(self, classifier):
        """Test edge case where all scores are one."""
        keyword_scores = {t: 1.0 for t in CLASSIFICATION_TYPES}
        semantic_scores = {t: 1.0 for t in CLASSIFICATION_TYPES}
        
        combined = classifier._combine_scores(keyword_scores, semantic_scores)
        
        for classification_type in CLASSIFICATION_TYPES:
            assert combined[classification_type] == 1.0, \
                f"Expected 1.0 for {classification_type}, got {combined[classification_type]}"
    
    def test_combine_scores_edge_case_mixed_extremes(self, classifier):
        """Test edge case with mixed extreme values."""
        keyword_scores = {
            ClassificationType.NAVIGATION.value: 1.0,
            ClassificationType.FEATURE_GUIDE.value: 0.0,
            ClassificationType.COMPANY_DATA.value: 1.0,
            ClassificationType.KENYA_GOVERNANCE.value: 0.0,
            ClassificationType.WEB_SEARCH.value: 1.0,
            ClassificationType.TIP.value: 0.0,
        }
        
        semantic_scores = {
            ClassificationType.NAVIGATION.value: 0.0,
            ClassificationType.FEATURE_GUIDE.value: 1.0,
            ClassificationType.COMPANY_DATA.value: 0.0,
            ClassificationType.KENYA_GOVERNANCE.value: 1.0,
            ClassificationType.WEB_SEARCH.value: 0.0,
            ClassificationType.TIP.value: 1.0,
        }
        
        combined = classifier._combine_scores(keyword_scores, semantic_scores)
        
        # Navigation: (1.0 * 0.7) + (0.0 * 0.3) = 0.7
        assert abs(combined[ClassificationType.NAVIGATION.value] - 0.7) < 0.001
        
        # Feature_Guide: (0.0 * 0.7) + (1.0 * 0.3) = 0.3
        assert abs(combined[ClassificationType.FEATURE_GUIDE.value] - 0.3) < 0.001
        
        # Company_Data: (1.0 * 0.7) + (0.0 * 0.3) = 0.7
        assert abs(combined[ClassificationType.COMPANY_DATA.value] - 0.7) < 0.001
        
        # Kenya_Governance: (0.0 * 0.7) + (1.0 * 0.3) = 0.3
        assert abs(combined[ClassificationType.KENYA_GOVERNANCE.value] - 0.3) < 0.001
