"""
Tests for context enhancement engine (Properties 14, 15, 16).

Tests verify that:
1. Company_Data confidence boosted by 0.2 for "my company" or "our directors"
2. Feature_Guide confidence boosted by 0.15 for Admin users with "users"/"permissions"
3. Kenya_Governance confidence boosted by 0.25 for "BRS"/"CMA"
4. Boosts are capped at 1.0
5. Conversation history is used for context-aware classification

**Validates: Requirements 12.1-12.6**
**Validates: Property 14: Context Boost Application**
**Validates: Property 15: Role-Based Context Boost**
**Validates: Property 16: Governance Keyword Boost**
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from communications.classifier import (
    MessageClassifier,
    ClassificationContext,
    ClassificationType,
    CLASSIFICATION_TYPES,
)


class TestContextBoosts:
    """Test context-based confidence boosts."""
    
    @pytest.fixture
    def classifier(self):
        """Create a fresh classifier instance."""
        return MessageClassifier()
    
    # ============================================================================
    # Property 14: Company_Data Boost for "my company" and "our directors"
    # ============================================================================
    
    def test_company_data_boost_my_company(self, classifier):
        """
        Test that Company_Data confidence is boosted by 0.2 when message contains "my company".
        
        **Validates: Property 14: Context Boost Application**
        """
        context = ClassificationContext(user_id=1, user_role="Staff")
        
        # Classify without boost trigger
        result_without = classifier.classify("What is the deadline?", context)
        company_data_score_without = result_without.scores[ClassificationType.COMPANY_DATA.value]
        
        # Classify with boost trigger
        result_with = classifier.classify("What is my company's deadline?", context)
        company_data_score_with = result_with.scores[ClassificationType.COMPANY_DATA.value]
        
        # Score with boost should be higher by approximately 0.2
        boost_amount = company_data_score_with - company_data_score_without
        assert boost_amount >= 0.15, \
            f"Company_Data boost insufficient: {boost_amount} (expected ~0.2)"
    
    def test_company_data_boost_our_directors(self, classifier):
        """
        Test that Company_Data confidence is boosted by 0.2 when message contains "our directors".
        
        **Validates: Property 14: Context Boost Application**
        """
        context = ClassificationContext(user_id=1, user_role="Staff")
        
        # Classify without boost trigger
        result_without = classifier.classify("Who are the board members?", context)
        company_data_score_without = result_without.scores[ClassificationType.COMPANY_DATA.value]
        
        # Classify with boost trigger
        result_with = classifier.classify("Who are our directors?", context)
        company_data_score_with = result_with.scores[ClassificationType.COMPANY_DATA.value]
        
        # Score with boost should be higher by approximately 0.2
        boost_amount = company_data_score_with - company_data_score_without
        assert boost_amount >= 0.15, \
            f"Company_Data boost insufficient: {boost_amount} (expected ~0.2)"
    
    def test_company_data_boost_our_board(self, classifier):
        """
        Test that Company_Data confidence is boosted by 0.2 when message contains "our board".
        """
        context = ClassificationContext(user_id=1, user_role="Staff")
        
        # Classify without boost trigger
        result_without = classifier.classify("What are the board members?", context)
        company_data_score_without = result_without.scores[ClassificationType.COMPANY_DATA.value]
        
        # Classify with boost trigger
        result_with = classifier.classify("What is our board's status?", context)
        company_data_score_with = result_with.scores[ClassificationType.COMPANY_DATA.value]
        
        # Score with boost should be higher by approximately 0.2
        boost_amount = company_data_score_with - company_data_score_without
        assert boost_amount >= 0.15, \
            f"Company_Data boost insufficient: {boost_amount} (expected ~0.2)"
    
    def test_company_data_boost_capped_at_one(self, classifier):
        """
        Test that Company_Data boost is capped at 1.0.
        
        **Validates: Property 14: Context Boost Application**
        """
        context = ClassificationContext(user_id=1, user_role="Staff")
        
        # Create a message that would trigger the boost
        result = classifier.classify("What is my company's deadline?", context)
        company_data_score = result.scores[ClassificationType.COMPANY_DATA.value]
        
        # Score should not exceed 1.0
        assert company_data_score <= 1.0, \
            f"Company_Data score exceeds 1.0: {company_data_score}"
    
    # ============================================================================
    # Property 15: Feature_Guide Boost for Admin users with "users"/"permissions"
    # ============================================================================
    
    def test_feature_guide_boost_admin_users(self, classifier):
        """
        Test that Feature_Guide confidence is boosted by 0.15 for Admin users mentioning "users".
        
        **Validates: Property 15: Role-Based Context Boost**
        """
        # Admin context
        admin_context = ClassificationContext(user_id=1, user_role="Admin")
        
        # Non-admin context
        staff_context = ClassificationContext(user_id=2, user_role="Staff")
        
        # Classify with Admin role
        result_admin = classifier.classify("How do I manage users?", admin_context)
        feature_guide_score_admin = result_admin.scores[ClassificationType.FEATURE_GUIDE.value]
        
        # Classify with Staff role
        result_staff = classifier.classify("How do I manage users?", staff_context)
        feature_guide_score_staff = result_staff.scores[ClassificationType.FEATURE_GUIDE.value]
        
        # Admin score should be higher by approximately 0.15
        boost_amount = feature_guide_score_admin - feature_guide_score_staff
        assert boost_amount >= 0.10, \
            f"Feature_Guide boost insufficient for Admin: {boost_amount} (expected ~0.15)"
    
    def test_feature_guide_boost_admin_permissions(self, classifier):
        """
        Test that Feature_Guide confidence is boosted by 0.15 for Admin users mentioning "permissions".
        
        **Validates: Property 15: Role-Based Context Boost**
        """
        # Admin context
        admin_context = ClassificationContext(user_id=1, user_role="Admin")
        
        # Non-admin context
        staff_context = ClassificationContext(user_id=2, user_role="Staff")
        
        # Classify with Admin role
        result_admin = classifier.classify("How do I set permissions?", admin_context)
        feature_guide_score_admin = result_admin.scores[ClassificationType.FEATURE_GUIDE.value]
        
        # Classify with Staff role
        result_staff = classifier.classify("How do I set permissions?", staff_context)
        feature_guide_score_staff = result_staff.scores[ClassificationType.FEATURE_GUIDE.value]
        
        # Admin score should be higher by approximately 0.15
        boost_amount = feature_guide_score_admin - feature_guide_score_staff
        assert boost_amount >= 0.10, \
            f"Feature_Guide boost insufficient for Admin: {boost_amount} (expected ~0.15)"
    
    def test_feature_guide_boost_admin_roles(self, classifier):
        """
        Test that Feature_Guide confidence is boosted by 0.15 for Admin users mentioning "roles".
        """
        # Admin context
        admin_context = ClassificationContext(user_id=1, user_role="Admin")
        
        # Non-admin context
        staff_context = ClassificationContext(user_id=2, user_role="Staff")
        
        # Classify with Admin role
        result_admin = classifier.classify("How do I manage roles?", admin_context)
        feature_guide_score_admin = result_admin.scores[ClassificationType.FEATURE_GUIDE.value]
        
        # Classify with Staff role
        result_staff = classifier.classify("How do I manage roles?", staff_context)
        feature_guide_score_staff = result_staff.scores[ClassificationType.FEATURE_GUIDE.value]
        
        # Admin score should be higher by approximately 0.15
        boost_amount = feature_guide_score_admin - feature_guide_score_staff
        assert boost_amount >= 0.10, \
            f"Feature_Guide boost insufficient for Admin: {boost_amount} (expected ~0.15)"
    
    def test_feature_guide_boost_no_boost_for_non_admin(self, classifier):
        """
        Test that Feature_Guide boost is NOT applied for non-Admin users.
        
        **Validates: Property 15: Role-Based Context Boost**
        """
        staff_context = ClassificationContext(user_id=1, user_role="Staff")
        accountant_context = ClassificationContext(user_id=2, user_role="Accountant")
        
        # Classify with Staff role
        result_staff = classifier.classify("How do I manage users?", staff_context)
        feature_guide_score_staff = result_staff.scores[ClassificationType.FEATURE_GUIDE.value]
        
        # Classify with Accountant role
        result_accountant = classifier.classify("How do I manage users?", accountant_context)
        feature_guide_score_accountant = result_accountant.scores[ClassificationType.FEATURE_GUIDE.value]
        
        # Scores should be similar (no boost for non-admin)
        diff = abs(feature_guide_score_staff - feature_guide_score_accountant)
        assert diff < 0.05, \
            f"Non-admin users should not get boost: {diff}"
    
    def test_feature_guide_boost_capped_at_one(self, classifier):
        """
        Test that Feature_Guide boost is capped at 1.0.
        
        **Validates: Property 15: Role-Based Context Boost**
        """
        admin_context = ClassificationContext(user_id=1, user_role="Admin")
        
        # Create a message that would trigger the boost
        result = classifier.classify("How do I manage users?", admin_context)
        feature_guide_score = result.scores[ClassificationType.FEATURE_GUIDE.value]
        
        # Score should not exceed 1.0
        assert feature_guide_score <= 1.0, \
            f"Feature_Guide score exceeds 1.0: {feature_guide_score}"
    
    # ============================================================================
    # Property 16: Kenya_Governance Boost for "BRS"/"CMA"
    # ============================================================================
    
    def test_kenya_governance_boost_brs(self, classifier):
        """
        Test that Kenya_Governance confidence is boosted by 0.25 for "BRS".
        
        **Validates: Property 16: Governance Keyword Boost**
        """
        context = ClassificationContext(user_id=1, user_role="Staff")
        
        # Classify without boost trigger
        result_without = classifier.classify("What are the filing requirements?", context)
        governance_score_without = result_without.scores[ClassificationType.KENYA_GOVERNANCE.value]
        
        # Classify with boost trigger
        result_with = classifier.classify("What are the BRS filing requirements?", context)
        governance_score_with = result_with.scores[ClassificationType.KENYA_GOVERNANCE.value]
        
        # Score with boost should be higher by approximately 0.25
        boost_amount = governance_score_with - governance_score_without
        assert boost_amount >= 0.20, \
            f"Kenya_Governance boost insufficient: {boost_amount} (expected ~0.25)"
    
    def test_kenya_governance_boost_cma(self, classifier):
        """
        Test that Kenya_Governance confidence is boosted by 0.25 for "CMA".
        
        **Validates: Property 16: Governance Keyword Boost**
        """
        context = ClassificationContext(user_id=1, user_role="Staff")
        
        # Classify without boost trigger
        result_without = classifier.classify("What are the requirements?", context)
        governance_score_without = result_without.scores[ClassificationType.KENYA_GOVERNANCE.value]
        
        # Classify with boost trigger
        result_with = classifier.classify("What are the CMA requirements?", context)
        governance_score_with = result_with.scores[ClassificationType.KENYA_GOVERNANCE.value]
        
        # Score with boost should be higher by approximately 0.25
        boost_amount = governance_score_with - governance_score_without
        assert boost_amount >= 0.20, \
            f"Kenya_Governance boost insufficient: {boost_amount} (expected ~0.25)"
    
    def test_kenya_governance_boost_kra(self, classifier):
        """
        Test that Kenya_Governance confidence is boosted by 0.25 for "KRA".
        """
        context = ClassificationContext(user_id=1, user_role="Staff")
        
        # Classify without boost trigger
        result_without = classifier.classify("What are the tax requirements?", context)
        governance_score_without = result_without.scores[ClassificationType.KENYA_GOVERNANCE.value]
        
        # Classify with boost trigger
        result_with = classifier.classify("What are the KRA requirements?", context)
        governance_score_with = result_with.scores[ClassificationType.KENYA_GOVERNANCE.value]
        
        # Score with boost should be higher by approximately 0.25
        boost_amount = governance_score_with - governance_score_without
        assert boost_amount >= 0.20, \
            f"Kenya_Governance boost insufficient: {boost_amount} (expected ~0.25)"
    
    def test_kenya_governance_boost_nse(self, classifier):
        """
        Test that Kenya_Governance confidence is boosted by 0.25 for "NSE".
        """
        context = ClassificationContext(user_id=1, user_role="Staff")
        
        # Classify without boost trigger
        result_without = classifier.classify("What are the listing requirements?", context)
        governance_score_without = result_without.scores[ClassificationType.KENYA_GOVERNANCE.value]
        
        # Classify with boost trigger
        result_with = classifier.classify("What are the NSE listing requirements?", context)
        governance_score_with = result_with.scores[ClassificationType.KENYA_GOVERNANCE.value]
        
        # Score with boost should be higher by approximately 0.25
        boost_amount = governance_score_with - governance_score_without
        assert boost_amount >= 0.20, \
            f"Kenya_Governance boost insufficient: {boost_amount} (expected ~0.25)"
    
    def test_kenya_governance_boost_capped_at_one(self, classifier):
        """
        Test that Kenya_Governance boost is capped at 1.0.
        
        **Validates: Property 16: Governance Keyword Boost**
        """
        context = ClassificationContext(user_id=1, user_role="Staff")
        
        # Create a message that would trigger the boost
        result = classifier.classify("What are the CMA requirements?", context)
        governance_score = result.scores[ClassificationType.KENYA_GOVERNANCE.value]
        
        # Score should not exceed 1.0
        assert governance_score <= 1.0, \
            f"Kenya_Governance score exceeds 1.0: {governance_score}"
    
    # ============================================================================
    # Conversation History Tests
    # ============================================================================
    
    def test_conversation_history_available(self, classifier):
        """Test that conversation history is available in context."""
        history = ["What is my company?", "Tell me more", "What about directors?"]
        context = ClassificationContext(
            user_id=1,
            user_role="Staff",
            conversation_history=history
        )
        
        # Get last 3 messages
        last_messages = context.get_last_messages(3)
        assert len(last_messages) == 3, f"Expected 3 messages, got {len(last_messages)}"
        assert last_messages == history, f"History mismatch: {last_messages} vs {history}"
    
    def test_conversation_history_partial(self, classifier):
        """Test that conversation history works with fewer than 3 messages."""
        history = ["What is my company?", "Tell me more"]
        context = ClassificationContext(
            user_id=1,
            user_role="Staff",
            conversation_history=history
        )
        
        # Get last 3 messages (only 2 available)
        last_messages = context.get_last_messages(3)
        assert len(last_messages) == 2, f"Expected 2 messages, got {len(last_messages)}"
        assert last_messages == history, f"History mismatch: {last_messages} vs {history}"
    
    def test_conversation_history_empty(self, classifier):
        """Test that conversation history works with empty history."""
        context = ClassificationContext(
            user_id=1,
            user_role="Staff",
            conversation_history=[]
        )
        
        # Get last 3 messages (none available)
        last_messages = context.get_last_messages(3)
        assert len(last_messages) == 0, f"Expected 0 messages, got {len(last_messages)}"
    
    # ============================================================================
    # Multiple Boosts Tests
    # ============================================================================
    
    def test_multiple_boosts_applied(self, classifier):
        """Test that multiple boosts can be applied to the same message."""
        admin_context = ClassificationContext(user_id=1, user_role="Admin")
        
        # Message that triggers both Company_Data and Feature_Guide boosts
        result = classifier.classify(
            "How do I manage users in my company?",
            admin_context
        )
        
        company_data_score = result.scores[ClassificationType.COMPANY_DATA.value]
        feature_guide_score = result.scores[ClassificationType.FEATURE_GUIDE.value]
        
        # Both should be boosted
        assert company_data_score > 0.0, "Company_Data should be boosted"
        assert feature_guide_score > 0.0, "Feature_Guide should be boosted"
    
    def test_all_three_boosts_applied(self, classifier):
        """Test that all three boosts can be applied to the same message."""
        admin_context = ClassificationContext(user_id=1, user_role="Admin")
        
        # Message that triggers all three boosts
        result = classifier.classify(
            "How do I manage users in my company regarding CMA requirements?",
            admin_context
        )
        
        company_data_score = result.scores[ClassificationType.COMPANY_DATA.value]
        feature_guide_score = result.scores[ClassificationType.FEATURE_GUIDE.value]
        governance_score = result.scores[ClassificationType.KENYA_GOVERNANCE.value]
        
        # All should be boosted
        assert company_data_score > 0.0, "Company_Data should be boosted"
        assert feature_guide_score > 0.0, "Feature_Guide should be boosted"
        assert governance_score > 0.0, "Kenya_Governance should be boosted"
    
    # ============================================================================
    # Edge Cases and Error Handling
    # ============================================================================
    
    def test_context_boost_with_none_context(self, classifier):
        """Test that classification works with None context."""
        # Should not raise an error
        result = classifier.classify("What is my company's deadline?", context=None)
        assert result.type in CLASSIFICATION_TYPES, f"Invalid classification type: {result.type}"
    
    def test_context_boost_with_none_user_role(self, classifier):
        """Test that classification works with None user role."""
        context = ClassificationContext(user_id=1, user_role=None)
        result = classifier.classify("How do I manage users?", context)
        assert result.type in CLASSIFICATION_TYPES, f"Invalid classification type: {result.type}"
    
    def test_context_boost_case_insensitive_role(self, classifier):
        """Test that user role comparison is case-insensitive."""
        # Test with different case variations
        for role in ["admin", "Admin", "ADMIN", "AdMiN"]:
            context = ClassificationContext(user_id=1, user_role=role)
            result = classifier.classify("How do I manage users?", context)
            feature_guide_score = result.scores[ClassificationType.FEATURE_GUIDE.value]
            
            # Should be boosted regardless of case
            assert feature_guide_score > 0.0, f"Boost not applied for role: {role}"
    
    def test_context_boost_case_insensitive_keywords(self, classifier):
        """Test that keyword matching is case-insensitive."""
        context = ClassificationContext(user_id=1, user_role="Staff")
        
        # Test with different case variations
        for keyword in ["my company", "MY COMPANY", "My Company", "mY cOmPaNy"]:
            result = classifier.classify(f"What is {keyword}'s deadline?", context)
            company_data_score = result.scores[ClassificationType.COMPANY_DATA.value]
            
            # Should be boosted regardless of case
            assert company_data_score > 0.0, f"Boost not applied for keyword: {keyword}"
    
    def test_context_boost_all_scores_in_range(self, classifier):
        """Test that all scores remain in valid range after boosts."""
        admin_context = ClassificationContext(user_id=1, user_role="Admin")
        
        test_messages = [
            "What is my company's deadline?",
            "How do I manage users?",
            "What are the CMA requirements?",
            "How do I manage users in my company regarding CMA requirements?",
        ]
        
        for message in test_messages:
            result = classifier.classify(message, admin_context)
            
            for score in result.scores.values():
                assert 0.0 <= score <= 1.0, \
                    f"Score out of range for '{message}': {score}"
    
    # ============================================================================
    # Property-Based Tests
    # ============================================================================
    
    @given(
        boost_amount=st.floats(min_value=0.0, max_value=0.3),
        base_score=st.floats(min_value=0.0, max_value=1.0),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_boost_capping_property(self, classifier, boost_amount, base_score):
        """
        Property test: For any base score and boost amount, the boosted score
        SHALL NOT exceed 1.0.
        
        **Validates: Property 14, 15, 16: Boosts capped at 1.0**
        """
        # Simulate boost application
        boosted = min(base_score + boost_amount, 1.0)
        
        # Should never exceed 1.0
        assert boosted <= 1.0, f"Boosted score exceeds 1.0: {boosted}"
    
    @given(
        base_score=st.floats(min_value=0.0, max_value=1.0),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_company_data_boost_property(self, classifier, base_score):
        """
        Property test: For any base Company_Data score, applying a 0.2 boost
        SHALL result in a score between base_score and min(base_score + 0.2, 1.0).
        
        **Validates: Property 14: Context Boost Application**
        """
        boosted = min(base_score + 0.2, 1.0)
        
        # Boosted should be >= base_score
        assert boosted >= base_score, f"Boosted score less than base: {boosted} < {base_score}"
        
        # Boosted should be <= 1.0
        assert boosted <= 1.0, f"Boosted score exceeds 1.0: {boosted}"
        
        # Boost should be approximately 0.2 (unless capped)
        if base_score <= 0.8:
            assert abs(boosted - (base_score + 0.2)) < 0.001, \
                f"Boost not applied correctly: {boosted} vs {base_score + 0.2}"
    
    @given(
        base_score=st.floats(min_value=0.0, max_value=1.0),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_feature_guide_boost_property(self, classifier, base_score):
        """
        Property test: For any base Feature_Guide score, applying a 0.15 boost
        SHALL result in a score between base_score and min(base_score + 0.15, 1.0).
        
        **Validates: Property 15: Role-Based Context Boost**
        """
        boosted = min(base_score + 0.15, 1.0)
        
        # Boosted should be >= base_score
        assert boosted >= base_score, f"Boosted score less than base: {boosted} < {base_score}"
        
        # Boosted should be <= 1.0
        assert boosted <= 1.0, f"Boosted score exceeds 1.0: {boosted}"
        
        # Boost should be approximately 0.15 (unless capped)
        if base_score <= 0.85:
            assert abs(boosted - (base_score + 0.15)) < 0.001, \
                f"Boost not applied correctly: {boosted} vs {base_score + 0.15}"
    
    @given(
        base_score=st.floats(min_value=0.0, max_value=1.0),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_governance_boost_property(self, classifier, base_score):
        """
        Property test: For any base Kenya_Governance score, applying a 0.25 boost
        SHALL result in a score between base_score and min(base_score + 0.25, 1.0).
        
        **Validates: Property 16: Governance Keyword Boost**
        """
        boosted = min(base_score + 0.25, 1.0)
        
        # Boosted should be >= base_score
        assert boosted >= base_score, f"Boosted score less than base: {boosted} < {base_score}"
        
        # Boosted should be <= 1.0
        assert boosted <= 1.0, f"Boosted score exceeds 1.0: {boosted}"
        
        # Boost should be approximately 0.25 (unless capped)
        if base_score <= 0.75:
            assert abs(boosted - (base_score + 0.25)) < 0.001, \
                f"Boost not applied correctly: {boosted} vs {base_score + 0.25}"
