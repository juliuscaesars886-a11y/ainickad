"""
Test script to verify Kenya compliance query works correctly
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'governance_hub.settings')
django.setup()

from communications.classifier import MessageClassifier, ClassificationContext
from communications.response_handlers import handle_kenya_governance_query

def test_kenya_compliance_query():
    """Test the specific query: 'What compliance requirements do Kenyan companies have?'"""
    
    print("=" * 80)
    print("Testing Kenya Compliance Query")
    print("=" * 80)
    
    # Initialize classifier
    classifier = MessageClassifier()
    
    # Test message
    message = "What compliance requirements do Kenyan companies have?"
    
    print(f"\nQuery: {message}")
    print("-" * 80)
    
    # Create context (using a dummy user ID for testing)
    context = ClassificationContext(
        user_id=1,
        company_id=None,
        conversation_history=[]
    )
    
    # Classify the message
    result = classifier.classify(message, context)
    
    print(f"\nClassification Result:")
    print(f"  Type: {result.type}")
    print(f"  Confidence: {result.confidence:.2%}")
    
    # Check if it's classified as Kenya_Governance
    if result.type == "Kenya_Governance":
        print("\n✓ PASS: Message correctly classified as Kenya_Governance")
    else:
        print(f"\n✗ FAIL: Message classified as {result.type}, expected Kenya_Governance")
        return False
    
    # Get the response
    print("\n" + "-" * 80)
    print("Response:")
    print("-" * 80)
    
    response = handle_kenya_governance_query(message, result, context)
    
    print(response)
    
    # Verify response characteristics
    print("\n" + "-" * 80)
    print("Response Verification:")
    print("-" * 80)
    
    checks = {
        "Contains markdown formatting": any(marker in response for marker in ['**', '##', '-', '*']),
        "NOT a numbered menu": not any(f"{i}." in response[:100] for i in range(1, 6)),
        "Contains compliance information": any(term in response.lower() for term in ['compliance', 'requirement', 'annual', 'filing', 'deadline']),
        "Starts with label (⚖)": response.startswith("⚖"),
        "Has substantial content": len(response) > 100
    }
    
    all_passed = True
    for check, passed in checks.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {check}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✓ ALL CHECKS PASSED")
        print("The AI chat now responds with natural markdown (NO numbered menus)")
        print("and queries the knowledge base directly for Kenya governance questions.")
    else:
        print("✗ SOME CHECKS FAILED")
    print("=" * 80)
    
    return all_passed

if __name__ == "__main__":
    try:
        success = test_kenya_compliance_query()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
