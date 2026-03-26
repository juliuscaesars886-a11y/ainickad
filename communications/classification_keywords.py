"""
Keyword Dictionaries for Message Classification

Defines keyword dictionaries for each classification type. Keywords are used for
fast rule-based classification. Each keyword has a weight (0.0-1.0) that affects
the confidence score. Higher weight keywords are stronger indicators of a classification type.

This file is the single source of truth for classification keywords. Update keywords here
to improve classification accuracy without changing code.
"""

from communications.classifier import Keyword, ClassificationType

# Navigation keywords: "How do I...", "Where is...", "How to..."
NAVIGATION_KEYWORDS = [
    # Primary navigation indicators
    Keyword("how do i", weight=1.0),
    Keyword("how to", weight=0.95),
    Keyword("where is", weight=0.9),
    Keyword("where can i", weight=0.9),
    Keyword("how can i", weight=0.85),
    Keyword("find", weight=0.7),
    Keyword("locate", weight=0.8),
    Keyword("access", weight=0.75),
    Keyword("navigate", weight=0.85),
    Keyword("go to", weight=0.8),
    Keyword("click", weight=0.75),
    Keyword("section", weight=0.6),
    Keyword("menu", weight=0.65),
    Keyword("button", weight=0.65),
    Keyword("tab", weight=0.65),
    Keyword("page", weight=0.6),
    Keyword("dashboard", weight=0.7),
    Keyword("sidebar", weight=0.75),
    Keyword("help", weight=0.7),
    Keyword("guide", weight=0.65),
]

# Feature Guide keywords: "What does X do?", "How does X work?"
FEATURE_GUIDE_KEYWORDS = [
    # Primary feature guide indicators
    Keyword("what does", weight=1.0),
    Keyword("how does", weight=1.0),
    Keyword("what is", weight=0.8),
    Keyword("explain", weight=0.8),
    Keyword("describe", weight=0.75),
    Keyword("tell me about", weight=0.75),
    Keyword("what's the", weight=0.7),
    Keyword("what are", weight=0.7),
    Keyword("purpose of", weight=0.8),
    Keyword("function of", weight=0.8),
    Keyword("use of", weight=0.75),
    Keyword("feature", weight=0.7),
    Keyword("capability", weight=0.7),
    Keyword("tool", weight=0.65),
    Keyword("works", weight=0.6),
    Keyword("do", weight=0.5),
]

# Company Data keywords: "My deadline", "Our board", "My company"
COMPANY_DATA_KEYWORDS = [
    # Primary company data indicators
    Keyword("my company", weight=1.0),
    Keyword("our company", weight=1.0),
    Keyword("our board", weight=0.95),
    Keyword("my deadline", weight=0.95),
    Keyword("our deadline", weight=0.95),
    Keyword("my tasks", weight=0.9),
    Keyword("my progress", weight=0.9),
    Keyword("our directors", weight=0.95),
    Keyword("our staff", weight=0.9),
    Keyword("our documents", weight=0.9),
    Keyword("my documents", weight=0.9),
    Keyword("company data", weight=0.85),
    Keyword("company information", weight=0.85),
    Keyword("company profile", weight=0.85),
    Keyword("company details", weight=0.85),
    Keyword("registration number", weight=0.8),
    Keyword("tax id", weight=0.8),
    Keyword("compliance score", weight=0.85),
    Keyword("health score", weight=0.85),
    Keyword("pending actions", weight=0.8),
    
    # Additional company-specific keywords to improve accuracy
    Keyword("our next", weight=0.85),  # "our next annual return deadline"
    Keyword("our upcoming", weight=0.85),  # "our upcoming compliance deadlines"
    Keyword("upcoming compliance", weight=0.9),  # "upcoming compliance deadlines"
    Keyword("upcoming deadlines", weight=0.9),
    Keyword("what documents have we", weight=0.9),  # "what documents have we uploaded"
    Keyword("what documents are", weight=0.85),  # "what documents are pending"
    Keyword("we uploaded", weight=0.85),
    Keyword("we have", weight=0.75),  # "what documents we have"
    Keyword("our beneficial", weight=0.9),  # "our beneficial ownership"
    Keyword("beneficial ownership structure", weight=0.95),  # More specific
    Keyword("our ownership", weight=0.85),
    Keyword("ownership structure", weight=0.9),
    Keyword("what board meetings", weight=0.9),  # "what board meetings are scheduled"
    Keyword("our meetings", weight=0.85),
    Keyword("scheduled", weight=0.7),  # company-specific scheduling
    Keyword("pending review", weight=0.8),  # company documents pending review
    
    # Pronouns that indicate company-specific queries
    Keyword("my", weight=0.6),  # General possessive
    Keyword("our", weight=0.6),  # General possessive
    Keyword("we", weight=0.5),   # Company reference
]

# Kenya Governance keywords: CMA, Companies Act, BRS, NSE, KRA
KENYA_GOVERNANCE_KEYWORDS = [
    # Regulatory bodies and acts
    Keyword("cma", weight=1.0),
    Keyword("companies act", weight=1.0),
    Keyword("brs", weight=1.0),
    Keyword("nse", weight=0.95),
    Keyword("kra", weight=0.95),
    Keyword("capital markets authority", weight=0.95),
    Keyword("business registration service", weight=0.95),
    Keyword("nairobi securities exchange", weight=0.95),
    Keyword("kenya revenue authority", weight=0.95),
    
    # Compliance and regulations
    Keyword("compliance", weight=0.85),
    Keyword("regulation", weight=0.8),
    Keyword("requirement", weight=0.75),
    Keyword("penalty", weight=0.8),
    Keyword("fine", weight=0.75),
    Keyword("filing", weight=0.8),
    Keyword("submission", weight=0.75),
    Keyword("deadline", weight=0.7),
    Keyword("annual return", weight=0.9),
    Keyword("agm", weight=0.85),
    Keyword("board meeting", weight=0.75),
    Keyword("director", weight=0.7),
    Keyword("shareholder", weight=0.7),
    Keyword("governance", weight=0.8),
    Keyword("corporate", weight=0.7),
    Keyword("disclosure", weight=0.75),
    Keyword("beneficial ownership", weight=0.85),
    Keyword("form cr", weight=0.9),
    Keyword("cr12", weight=0.95),
    Keyword("cr5", weight=0.95),
    Keyword("cr6", weight=0.95),
    Keyword("cr7", weight=0.95),
    Keyword("cr19", weight=0.9),
]

# Web Search keywords: Outside domain questions
WEB_SEARCH_KEYWORDS = [
    # General knowledge indicators
    Keyword("what is", weight=0.5),  # Low weight - overlaps with other types
    Keyword("how", weight=0.4),  # Low weight - overlaps with other types
    Keyword("why", weight=0.6),
    Keyword("when", weight=0.6),
    Keyword("where", weight=0.4),  # Low weight - overlaps with navigation
    Keyword("who", weight=0.6),
    Keyword("tell me", weight=0.5),
    Keyword("explain", weight=0.4),  # Low weight - overlaps with feature guide
    Keyword("research", weight=0.8),
    Keyword("information about", weight=0.7),
    Keyword("news", weight=0.8),
    Keyword("current", weight=0.7),
    Keyword("latest", weight=0.7),
    Keyword("recent", weight=0.7),
    Keyword("international", weight=0.75),
    Keyword("global", weight=0.75),
    Keyword("world", weight=0.7),
    Keyword("country", weight=0.6),
    Keyword("industry", weight=0.65),
    Keyword("sector", weight=0.65),
    
    # External knowledge indicators to improve accuracy
    Keyword("cryptocurrency", weight=0.9),
    Keyword("blockchain", weight=0.9),
    Keyword("machine learning", weight=0.9),
    Keyword("artificial intelligence", weight=0.9),
    Keyword("cloud computing", weight=0.9),
    Keyword("project management", weight=0.8),
    Keyword("best practices", weight=0.8),
    Keyword("python programming", weight=0.9),
    Keyword("credit score", weight=0.9),  # Increased weight
    Keyword("improve my credit", weight=0.95),  # More specific
    Keyword("freelancing", weight=0.8),
    Keyword("tax implications", weight=0.8),
    Keyword("starting a business", weight=0.8),
    Keyword("history of", weight=0.8),  # "history of the stock market"
    Keyword("stock market", weight=0.85),
    Keyword("weather", weight=0.9),
    Keyword("president", weight=0.8),
    Keyword("capital", weight=0.7),  # "capital of Kenya"
    Keyword("headlines", weight=0.8),
    Keyword("technology trends", weight=0.8),
    Keyword("economic situation", weight=0.8),
    Keyword("market trends", weight=0.8),
    
    # Negative indicators for domain-specific terms (lower weights)
    Keyword("compliance", weight=0.2),  # Should favor Kenya_Governance
    Keyword("company", weight=0.2),     # Should favor Company_Data
    Keyword("feature", weight=0.2),     # Should favor Feature_Guide
    Keyword("navigate", weight=0.2),    # Should favor Navigation
]

# Tip keywords: Ambiguous or unclear messages
TIP_KEYWORDS = [
    # Primary ambiguity indicators
    Keyword("unclear", weight=0.9),
    Keyword("confused", weight=0.9),
    Keyword("not sure", weight=0.9),
    Keyword("don't understand", weight=0.9),
    Keyword("don't know", weight=0.85),
    Keyword("lost", weight=0.8),
    Keyword("having trouble", weight=0.8),
    Keyword("need help", weight=0.7),
    Keyword("can you help", weight=0.7),
    Keyword("assist me", weight=0.7),
    Keyword("can you clarify", weight=0.8),
    Keyword("can you explain", weight=0.6),  # Lower weight - overlaps with feature guide
    
    # Ambiguous question patterns that should trigger tip
    Keyword("what should i do", weight=0.85),
    Keyword("what does this mean", weight=0.85),  # Increased weight for ambiguity
    Keyword("what is this for", weight=0.85),     # Increased weight
    Keyword("this mean", weight=0.8),             # "what does this mean"
    Keyword("this for", weight=0.8),              # "what is this for"
    Keyword("where to start", weight=0.8),
    Keyword("i do not understand", weight=0.9),   # More specific
    Keyword("do not understand this", weight=0.95), # Very specific
    Keyword("understand this", weight=0.8),
    Keyword("i am", weight=0.4),  # "I am confused", "I am lost"
    Keyword("i'm", weight=0.4),   # "I'm confused", "I'm lost"
    
    # Very generic/fallback indicators - keep low weight
    Keyword("help", weight=0.3),  # Low weight - overlaps with navigation
    Keyword("what", weight=0.2),  # Very low weight - too generic
    Keyword("how", weight=0.2),   # Very low weight - too generic
    Keyword("?", weight=0.4),     # Question mark
]

# Keyword dictionaries mapping classification type to keywords
KEYWORD_DICTIONARIES = {
    ClassificationType.NAVIGATION.value: NAVIGATION_KEYWORDS,
    ClassificationType.FEATURE_GUIDE.value: FEATURE_GUIDE_KEYWORDS,
    ClassificationType.COMPANY_DATA.value: COMPANY_DATA_KEYWORDS,
    ClassificationType.KENYA_GOVERNANCE.value: KENYA_GOVERNANCE_KEYWORDS,
    ClassificationType.WEB_SEARCH.value: WEB_SEARCH_KEYWORDS,
    ClassificationType.TIP.value: TIP_KEYWORDS,
}


def get_keyword_dictionaries():
    """Get all keyword dictionaries."""
    return KEYWORD_DICTIONARIES


def reload_keywords():
    """Reload keyword dictionaries (for hot reload support)."""
    # This function can be called to reload keywords without restarting
    # Currently just returns the dictionaries, but can be extended for hot reload
    return KEYWORD_DICTIONARIES
