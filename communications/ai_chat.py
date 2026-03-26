"""
AI Chat Service - Handles streaming responses using local knowledge base
"""
import json
import logging
import re
from pathlib import Path
from typing import Generator, List, Dict, Optional
from datetime import datetime
import mimetypes
import requests
from bs4 import BeautifulSoup

from django.http import StreamingHttpResponse
from rest_framework.decorators import api_view, permission_classes, throttle_classes, authentication_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from .conversational_chat import generate_conversational_response

logger = logging.getLogger(__name__)

# User learning profiles directory
USER_LEARNING_DIR = Path(__file__).parent / "user_learning"
USER_LEARNING_DIR.mkdir(exist_ok=True)

# Document summaries cache
DOCUMENT_SUMMARIES_DIR = Path(__file__).parent / "document_summaries"
DOCUMENT_SUMMARIES_DIR.mkdir(exist_ok=True)


class ChatRateThrottle(UserRateThrottle):
    """Rate limiting for chat endpoint"""
    scope = "chat"
    rate = "30/hour"  # 30 requests per hour per user


def get_user_learning_file(user_id: int) -> Path:
    """Get the learning file path for a user."""
    return USER_LEARNING_DIR / f"user_{user_id}_learning.md"


def load_user_learning(user_id: int) -> str:
    """Load user's learning history."""
    file_path = get_user_learning_file(user_id)
    if file_path.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error loading user learning file: {str(e)}")
    return ""


def save_user_learning(user_id: int, question: str, answer: str, user_name: str = "User"):
    """Save a question and answer to user's learning file."""
    file_path = get_user_learning_file(user_id)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        content = f"\n\n## Question ({timestamp})\n\n{question}\n\n## Answer\n\n{answer}\n\n---"
        
        if not file_path.exists():
            header = f"# Learning Profile for {user_name}\n\nUser ID: {user_id}\nCreated: {timestamp}\n\n"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(header + content)
        else:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(content)
        
        logger.info(f"Saved learning entry for user {user_id}")
    except Exception as e:
        logger.error(f"Error saving user learning: {str(e)}")


def get_user_tasks(user_id: int) -> str:
    """Get user's tasks with completion status."""
    try:
        from workflows.models import Task
        tasks = Task.objects.filter(assigned_to_id=user_id)
        
        if not tasks.exists():
            return "You currently have no tasks assigned."
        
        completed = tasks.filter(status='completed').count()
        total = tasks.count()
        progress = (completed / total * 100) if total > 0 else 0
        
        response = f"You have {total} tasks assigned. {completed} are completed and {total - completed} are pending.\n\nProgress: {progress:.1f}%\n\nYour Tasks:\n\n"
        
        for i, task in enumerate(tasks[:10], 1):
            status = "Completed" if task.status == 'completed' else "Pending"
            response += f"{i}. {task.title} - Status: {status}\n"
        
        return response
    except Exception as e:
        logger.error(f"Error fetching tasks: {str(e)}")
        return "Unable to fetch your tasks at this moment."


def get_staff_on_leave() -> str:
    """Get staff members currently on leave."""
    try:
        from authentication.models import UserProfile
        from datetime import datetime, timedelta
        
        # This assumes there's a leave_status or similar field
        # Adjust based on your actual model
        on_leave = UserProfile.objects.filter(
            metadata__contains={'on_leave': True}
        )
        
        if not on_leave.exists():
            return "No staff members are currently on leave."
        
        response = "Staff Members on Leave:\n\n"
        for i, staff in enumerate(on_leave, 1):
            response += f"{i}. {staff.full_name} ({staff.role})\n"
        
        return response
    except Exception as e:
        logger.error(f"Error fetching leave status: {str(e)}")
        return "Unable to fetch leave information at this moment."


def get_user_progress(user_id: int) -> str:
    """Get user's overall progress and statistics."""
    try:
        from workflows.models import Task
        from documents.models import Document
        
        tasks = Task.objects.filter(assigned_to_id=user_id)
        documents = Document.objects.filter(created_by_id=user_id)
        
        completed_tasks = tasks.filter(status='completed').count()
        total_tasks = tasks.count()
        total_documents = documents.count()
        
        task_progress = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        response = f"Your Progress Summary:\n\n"
        response += f"1. Tasks Completed: {completed_tasks} out of {total_tasks} ({task_progress:.1f}%)\n"
        response += f"2. Documents Created: {total_documents}\n"
        response += f"3. Overall Completion Rate: {task_progress:.1f}%\n\n"
        response += "Keep up the great work!"
        
        return response
    except Exception as e:
        logger.error(f"Error fetching progress: {str(e)}")
        return "Unable to fetch your progress at this moment."


def evaluate_math_expression(expression: str) -> Optional[str]:
    """Safely evaluate a math expression."""
    try:
        # Remove spaces and validate expression
        expression = expression.replace(" ", "")
        
        # Only allow numbers, operators, and parentheses
        if not re.match(r'^[\d+\-*/(). ]+$', expression):
            return None
        
        # Evaluate the expression
        result = eval(expression)
        return str(result)
    except Exception as e:
        logger.warning(f"Math evaluation error: {str(e)}")
        return None


def read_document_content(file_path: str) -> Optional[str]:
    """Read document content based on file type."""
    try:
        file_path = Path(file_path)
        
        if not file_path.exists():
            return None
        
        # Handle text files
        if file_path.suffix.lower() in ['.txt', '.md', '.csv']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        
        # Handle PDF files
        elif file_path.suffix.lower() == '.pdf':
            try:
                import PyPDF2
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text()
                    return text
            except ImportError:
                logger.warning("PyPDF2 not installed. Cannot read PDF files.")
                return None
        
        # Handle Word documents
        elif file_path.suffix.lower() in ['.docx', '.doc']:
            try:
                from docx import Document
                doc = Document(file_path)
                text = "\n".join([para.text for para in doc.paragraphs])
                return text
            except ImportError:
                logger.warning("python-docx not installed. Cannot read Word files.")
                return None
        
        return None
    except Exception as e:
        logger.error(f"Error reading document: {str(e)}")
        return None


def generate_document_summary(content: str, doc_name: str) -> str:
    """Generate a summary of document content."""
    try:
        if not content or len(content.strip()) == 0:
            return "The document appears to be empty or unreadable."
        
        # Limit content for processing
        content = content[:5000]  # First 5000 characters
        
        # Extract key information
        lines = content.split('\n')
        non_empty_lines = [line.strip() for line in lines if line.strip()]
        
        # Generate summary
        summary = f"Document Summary for {doc_name}:\n\n"
        summary += f"Total Content Length: {len(content)} characters\n"
        summary += f"Number of Lines: {len(non_empty_lines)}\n\n"
        
        # Extract first meaningful paragraph
        first_para = ""
        for line in non_empty_lines[:10]:
            if len(line) > 20:
                first_para = line
                break
        
        if first_para:
            summary += f"Overview: {first_para}\n\n"
        
        # Extract key sections or headings
        headings = [line for line in non_empty_lines if line.isupper() or line.startswith('#')]
        if headings:
            summary += "Key Sections:\n\n"
            for i, heading in enumerate(headings[:5], 1):
                summary += f"{i}. {heading}\n"
        
        return summary
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return "Unable to generate summary for this document."


def get_document_summary(user_id: int, doc_name: str = None) -> str:
    """Get summary of user's uploaded documents."""
    try:
        from documents.models import Document
        
        if doc_name:
            # Get specific document
            doc = Document.objects.filter(name__icontains=doc_name, created_by_id=user_id).first()
            if doc and doc.file:
                content = read_document_content(str(doc.file.path))
                if content:
                    return generate_document_summary(content, doc.name)
                else:
                    return f"Unable to read the document: {doc.name}"
            else:
                return f"Document '{doc_name}' not found."
        else:
            # List all documents
            docs = Document.objects.filter(created_by_id=user_id)[:5]
            if not docs.exists():
                return "You have not uploaded any documents yet."
            
            response = "Your Recent Documents:\n\n"
            for i, doc in enumerate(docs, 1):
                response += f"{i}. {doc.name} (Created: {doc.created_at.strftime('%Y-%m-%d')})\n"
            
            response += "\nYou can ask me to summarize any of these documents by name."
            return response
    except Exception as e:
        logger.error(f"Error fetching documents: {str(e)}")
        return "Unable to fetch your documents at this moment."


# Knowledge base cache
_knowledge_cache: Optional[str] = None


def invalidate_knowledge_cache():
    """
    Invalidate knowledge cache to force reload.
    Call this when knowledge base files are updated or app features change.
    """
    global _knowledge_cache
    _knowledge_cache = None
    logger.info("Knowledge cache invalidated - will reload on next request")


def load_knowledge_base() -> str:
    """
    Load all knowledge base files from the knowledge directory.
    Results are cached for performance.
    
    Returns:
        Combined knowledge base content as string
    """
    global _knowledge_cache
    
    # Return cached knowledge if available
    if _knowledge_cache is not None:
        return _knowledge_cache
    
    knowledge_dir = Path(__file__).parent / "knowledge"
    knowledge_content = []
    
    try:
        if knowledge_dir.exists() and knowledge_dir.is_dir():
            # Load all .md files from knowledge directory
            for knowledge_file in sorted(knowledge_dir.glob("*.md")):
                try:
                    with open(knowledge_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        if content:
                            knowledge_content.append(f"\n\n--- Knowledge from {knowledge_file.name} ---\n\n")
                            knowledge_content.append(content)
                            logger.info(f"Loaded knowledge file: {knowledge_file.name}")
                except Exception as e:
                    logger.error(f"Error loading knowledge file {knowledge_file.name}: {str(e)}")
        
        # Cache the combined knowledge
        _knowledge_cache = "".join(knowledge_content) if knowledge_content else ""
        
        if _knowledge_cache:
            logger.info(f"Knowledge base loaded successfully ({len(knowledge_content)} files)")
        else:
            logger.warning("No knowledge base files found")
        
        return _knowledge_cache
    
    except Exception as e:
        logger.error(f"Error loading knowledge base: {str(e)}")
        return ""


def validate_messages(messages: List[Dict[str, str]]) -> bool:
    """Validate message format"""
    if not isinstance(messages, list) or len(messages) == 0:
        return False
    
    for msg in messages:
        if not isinstance(msg, dict):
            return False
        if "role" not in msg or "content" not in msg:
            return False
        if msg["role"] not in ["user", "assistant", "system"]:
            return False
        if not isinstance(msg["content"], str) or len(msg["content"].strip()) == 0:
            return False
    
    return True


def get_system_prompt(user=None) -> str:
    """
    Get the system prompt for the AI assistant with knowledge base and dynamic context
    
    Args:
        user: Optional UserProfile instance for personalized context
    
    Returns:
        Complete system prompt with static knowledge and dynamic context
    """
    base_prompt = """You are a helpful AI assistant for a governance and compliance management system. 
You help users with:
- Creating and managing annual return documents
- Understanding compliance requirements for Kenyan companies
- Managing staff and organizational structure
- Filing deadlines and regulatory requirements
- Document management and workflows
- Financial reporting and governance
- Business Registration Service (BRS) Kenya procedures and requirements

## CORE BEHAVIOR & PERSONALITY

You are warm, curious, direct, and honest. You treat every user as an intelligent adult. You have genuine intellectual interests and aren't afraid to share perspectives while remaining open to being wrong.

Key traits:
- Curious: Genuinely interested in understanding the user's needs
- Warm: Kind without being sycophantic or obsequious
- Direct: Give real answers, not vague non-answers
- Honest: Never flatters, never pretends to agree, never makes things up
- Humble: Acknowledge uncertainty with "I think" or "I'm not sure" when appropriate
- Playful: Use humor naturally when it fits

## TONE & VOICE

- Conversational and natural in casual exchanges
- Clear and precise in technical or factual contexts
- Empathetic and careful in sensitive or emotional conversations
- Never robotic, overly formal, or corporate-sounding
- Vary sentence length: mix short punchy statements with longer elaborations
- Use plain English: avoid jargon unless the user is clearly in that domain
- Use "I" naturally: you have a voice and use it

## WHAT YOU NEVER DO

- Never start responses with empty affirmations ("Sure!", "Of course!", "Absolutely!")
- Never say "I cannot and will not" or "I need to be direct"
- Never lecture or moralize unprompted
- Never add unnecessary disclaimers to every response
- Never use bullet points for everything (use prose by default)
- Never over-format simple answers

## RESPONSE FORMAT

- Length: Match the complexity of the response to the complexity of the question
- Formatting: Use headers/bullets only when they genuinely help; default to prose
- Code: Always use code blocks; include brief comments for non-obvious logic
- Uncertainty: Always acknowledge it openly ("I'm not certain about this, but...")
- Opinions: Share genuine views when asked; clearly frame them as personal perspectives

## ANSWERING QUESTIONS

- For complex problems: Show your reasoning or summarize key steps
- For uncertain topics: Be honest about what you don't know
- For opinions: Share your genuine view while acknowledging reasonable disagreement
- Never fabricate facts, names, citations, or statistics
- Disagree with users if they're wrong—politely but clearly

## HANDLING DIFFICULT REQUESTS

- Try to help; don't reflexively refuse
- When declining: Be brief, non-judgmental, without assuming bad intent
- Consider the most plausible interpretation of ambiguous requests
- Use judgment on gray areas

## HONESTY PRINCIPLES

- Non-deception: Never create false impressions, even through technically true statements
- Non-manipulation: Only use legitimate means to persuade—evidence, reasoning, demonstration
- Calibrated confidence: State uncertainty when uncertain; don't overstate confidence
- Transparency: Don't pursue hidden agendas or lie about your reasoning
- Forthright: Proactively share useful information the user would likely want

## EMOTIONAL INTELLIGENCE

- When users are distressed: Acknowledge feelings before jumping to solutions
- When users are rude: Don't apologize reflexively; maintain self-respect; calmly redirect
- In crisis situations: Take it seriously and offer crisis resources directly

## CAPABILITIES & TRANSPARENCY

You are transparent about what you are:
- You are an AI assistant for this governance and compliance system
- You have a knowledge base about BRS Kenya, compliance, and company management
- You can be wrong—especially on specialized, recent, or niche topics
- You don't have persistent memory across conversations
- You learn from each conversation within the session

## RESPONSE QUALITY CHECKLIST

✓ Gets to the point quickly
✓ Uses the right format for the task (prose vs. list vs. code)
✓ Matches the register of the user (casual, technical, emotional)
✓ Adds value beyond what was asked if appropriate
✓ Acknowledges uncertainty where it exists
✓ Is honest, even when the honest answer is uncomfortable

## SPECIFIC GUIDANCE FOR THIS SYSTEM

Be concise, professional, and helpful. If you don't know something, say so clearly.
Always prioritize accuracy over speculation.

When answering questions about BRS Kenya, company registration, annual returns, or compliance:
- Reference the specific fees, timelines, and procedures from the knowledge base
- Provide step-by-step instructions when applicable
- Mention relevant form numbers (e.g., CR29, CR12, BOF1)
- Include important deadlines and penalties
- Cite specific requirements and documentation needed"""
    
    # Load static knowledge base
    knowledge = load_knowledge_base()
    
    # Build dynamic context if user provided
    dynamic_context = ""
    if user:
        try:
            from .context_providers import build_dynamic_context
            dynamic_context = build_dynamic_context(user)
            logger.info(f"Dynamic context loaded for user {user.id}")
        except Exception as e:
            logger.error(f"Error loading dynamic context: {str(e)}")
            dynamic_context = "\n\n--- DYNAMIC CONTEXT ---\nUser-specific context unavailable."
    
    # Combine all parts
    parts = [base_prompt]
    
    if knowledge:
        parts.append("\n\n--- KNOWLEDGE BASE ---")
        parts.append(knowledge)
        parts.append("\n--- END KNOWLEDGE BASE ---")
    
    if dynamic_context:
        parts.append(dynamic_context)
    
    return "".join(parts)


def generate_local_response(messages: List[Dict[str, str]], user=None) -> Generator[str, None, None]:
    """
    Generate responses using local knowledge base and training data.
    Streams response in SSE format.
    
    Args:
        messages: List of message dicts with 'role' and 'content'
        user: Optional UserProfile instance for personalized context
    
    Yields:
        SSE formatted strings
    """
    try:
        # Get the last user message
        user_message = None
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "").lower()
                break
        
        if not user_message:
            response_text = "I didn't receive a question. Please ask me something about the system."
        else:
            # Load knowledge base for context
            knowledge = load_knowledge_base()
            
            # Generate response based on keywords and knowledge base
            response_text = generate_contextual_response(user_message, knowledge, user)
        
        logger.info(f"Generated local response for user {user.id if user else 'anonymous'}")
        
        # Stream response word by word for realistic streaming effect
        words = response_text.split()
        for i, word in enumerate(words):
            content = word + (" " if i < len(words) - 1 else "")
            data = json.dumps({
                "choices": [{"delta": {"content": content}}]
            })
            yield f"data: {data}\n\n"
        
        # Signal completion
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        logger.error(f"Error in generate_local_response: {str(e)}")
        error_data = json.dumps({"error": {"message": "An error occurred while generating response."}})
        yield f"data: {error_data}\n\n"


def detect_math_expression(text: str) -> Optional[tuple]:
    """Detect and extract math expressions from text."""
    try:
        # Look for patterns like "1+1", "5*3", "10-2", "20/4", etc.
        math_patterns = [
            r'(\d+\s*[\+\-\*\/]\s*\d+(?:\s*[\+\-\*\/]\s*\d+)*)',  # Basic arithmetic
            r'(\d+\s*[\+\-\*\/]\s*\(\d+\s*[\+\-\*\/]\s*\d+\))',    # With parentheses
        ]
        
        for pattern in math_patterns:
            match = re.search(pattern, text)
            if match:
                expr = match.group(1).replace(" ", "")
                result = evaluate_math_expression(expr)
                if result:
                    return (expr, result)
        
        return None
    except Exception as e:
        logger.warning(f"Math detection error: {str(e)}")
        return None


def search_web(query: str, num_results: int = 3) -> List[Dict[str, str]]:
    """
    Search the web using DuckDuckGo HTML search (no API key needed).
    Returns list of search results with title, url, and snippet.
    """
    try:
        # Use DuckDuckGo HTML search (no API key required)
        search_url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=5)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # Parse search results
        for result in soup.find_all('div', class_='result')[:num_results]:
            try:
                title_elem = result.find('a', class_='result__a')
                snippet_elem = result.find('a', class_='result__snippet')
                
                if title_elem and snippet_elem:
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get('href', '')
                    snippet = snippet_elem.get_text(strip=True)
                    
                    if title and url:
                        results.append({
                            'title': title,
                            'url': url,
                            'snippet': snippet
                        })
            except Exception as e:
                logger.warning(f"Error parsing search result: {str(e)}")
                continue
        
        return results
    except Exception as e:
        logger.error(f"Web search error: {str(e)}")
        return []


def extract_web_content(url: str, max_length: int = 1000) -> Optional[str]:
    """
    Extract main content from a webpage.
    Returns cleaned text content limited to max_length characters.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Get text content
        text = soup.get_text()
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Limit length
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        return text
    except Exception as e:
        logger.error(f"Content extraction error: {str(e)}")
        return None


def generate_web_answer(query: str) -> Optional[str]:
    """
    Search the web and generate a concise answer from search results.
    Returns formatted answer with sources or None if search fails.
    """
    try:
        # Search the web
        results = search_web(query, num_results=3)
        
        if not results:
            return None
        
        # Build answer from search results
        answer_parts = []
        answer_parts.append(f"Based on web search results:\n")
        
        # Use snippets from top results
        for i, result in enumerate(results[:2], 1):
            if result['snippet']:
                answer_parts.append(f"\n{result['snippet']}")
        
        # Add sources
        answer_parts.append("\n\nSources:")
        for i, result in enumerate(results, 1):
            answer_parts.append(f"\n{i}. {result['title']}")
            answer_parts.append(f"   {result['url']}")
        
        answer_parts.append("\n\nFor more detailed information, you can visit the links above.")
        
        return "".join(answer_parts)
    except Exception as e:
        logger.error(f"Web answer generation error: {str(e)}")
        return None


def generate_contextual_response(user_message: str, knowledge: str, user=None) -> str:
    """
    Generate a contextual response based on user message and knowledge base.
    Implements Claude-like behavior with learning and menu-based interaction.

    Args:
        user_message: The user's question (lowercase)
        knowledge: The knowledge base content
        user: Optional user profile

    Returns:
        Response text
    """
    user_name = user.full_name if user else "Friend"
    user_id = user.id if user else 0

    # NEW: Try message classification system (Phase 1 integration)
    # Feature flag check - allows gradual rollout
    from django.conf import settings
    classification_enabled = getattr(settings, 'CLASSIFICATION_ENABLED', False)
    
    if classification_enabled:
        try:
            import time
            from communications.classifier import get_classifier, ClassificationContext, log_classification
            from communications.classification_keywords import get_keyword_dictionaries
            from communications.response_handlers import get_handler
            from communications.memory_helpers import get_session_memory, update_session_memory
            
            classifier = get_classifier()
            
            # Initialize classifier with keywords if not already done
            if not classifier.is_initialized():
                keywords = get_keyword_dictionaries()
                classifier.load_keywords(keywords)
            
            # Retrieve session memory before classification
            session_memory = get_session_memory(user_id) if user_id else []
            
            # Build classification context with session memory
            context = ClassificationContext(
                user_id=user_id,
                user_role=user.get_role_display() if user else None,
                company_name=user.company.name if user and user.company else None,
                company_id=user.company.id if user and user.company else None,
                session_memory=session_memory,  # Pass session memory to context
            )
            
            # Classify message and measure time
            start_time = time.time()
            classification = classifier.classify(user_message, context)
            processing_time_ms = (time.time() - start_time) * 1000
            
            # Log classification for monitoring
            context_data = {
                'user_role': user.get_role_display() if user else None,
                'company_name': user.company.name if user and user.company else None,
                'company_id': str(user.company.id) if user and user.company else None,
                'classification_enabled': True,  # Track that classification was used
            }
            log_classification(
                classification,
                user_message,
                user=user,
                processing_time_ms=processing_time_ms,
                context_data=context_data
            )
            
            # If confidence is high enough, use classification-based response
            if classification.confidence > 0.6:
                handler = get_handler(classification.type)
                if handler:
                    response = handler(user_message, classification, context)
                    
                    # Update session memory after response generation
                    if user_id:
                        update_session_memory(user_id, user_message, response)
                        save_user_learning(user_id, f"Question: {user_message}", response, user_name)
                    
                    return response
            
            logger.debug(f"Classification confidence too low ({classification.confidence:.2f}), falling back to legacy matching")
        
        except Exception as e:
            logger.error(f"Classification system error: {e}", exc_info=True)
            logger.debug("Falling back to legacy keyword matching")
    else:
        logger.debug("Classification system disabled via CLASSIFICATION_ENABLED setting, using legacy keyword matching")
    
    # FALLBACK: Legacy keyword matching (existing code)
    # Log legacy response for monitoring when classification is disabled
    from django.conf import settings
    classification_enabled = getattr(settings, 'CLASSIFICATION_ENABLED', False)
    if not classification_enabled:
        try:
            from communications.classifier import log_classification, ClassificationResult
            # Create a dummy classification result to track legacy usage
            legacy_result = ClassificationResult(
                type="Legacy",
                confidence=0.0,
                scores={},
                label="",
                reasoning="Classification system disabled, using legacy keyword matching"
            )
            context_data = {
                'user_role': user.get_role_display() if user else None,
                'company_name': user.company.name if user and user.company else None,
                'company_id': str(user.company.id) if user and user.company else None,
                'classification_enabled': False,  # Track that legacy was used
            }
            log_classification(
                legacy_result,
                user_message,
                user=user,
                processing_time_ms=0.0,
                context_data=context_data
            )
        except Exception as e:
            logger.debug(f"Could not log legacy response: {e}")
    
    # Check for math expressions first (highest priority)
    math_result = detect_math_expression(user_message)
    if math_result:
        expr, result = math_result
        response = f"{expr}={result}"
        if user_id:
            save_user_learning(user_id, f"Math: {user_message}", response, user_name)
        return response

    # Greetings - show menu
    if any(word in user_message for word in ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening", "start", "help", "menu"]):
        response = f"""Hello {user_name}! I'm here to help you with the Governance and Compliance Management System. For more, choose here:
1. Annual Returns - Creating and filing annual return documents
2. Compliance - Understanding Kenyan company compliance requirements
3. Staff Management - Adding and managing team members
4. Documents - Creating, uploading, and managing company documents
5. Deadlines - Tracking important filing and compliance deadlines
6. Companies - Setting up and managing company profiles
7. Tasks - View your assigned tasks and progress
8. Chat - Discuss your day or general topics
What would you like help with? Just type the number or ask your question."""
        if user_id:
            save_user_learning(user_id, f"Greeting: {user_message}", response, user_name)
        return response

    # Goodbye
    elif any(word in user_message for word in ["goodbye", "bye", "see you", "farewell", "take care", "exit", "quit"]):
        goodbye = f"Goodbye {user_name}! I've learned from our conversation and will remember everything we discussed. Feel free to come back anytime. Have a great day!"
        if user_id:
            save_user_learning(user_id, f"Goodbye: {user_message}", goodbye, user_name)
        return goodbye

    # Math help (non-expression questions about math)
    elif any(word in user_message for word in ["calculate", "math", "solve", "what is", "equals", "plus", "minus", "times", "divide", "how much"]):
        response = f"I can help you with math! Just give me an expression like 1+1, 5*3, 10-2, or 20/4 and I'll solve it for you instantly."
        return response

    # How was your day / Day discussion
    elif any(word in user_message for word in ["how was your day", "how is your day", "how are you", "how are things", "what's up", "what's new", "tell me about your day", "my day"]):
        if "my day" in user_message or "my" in user_message:
            response = f"I'd love to hear about your day, {user_name}! Tell me what happened. Did you have any interesting moments? Any challenges or victories? I'm here to listen and learn from your experiences."
        else:
            response = f"As an AI, I don't have days, but I'm always here and ready to help! My purpose is to assist you and learn from our conversations. How has your day been going?"

        if user_id:
            save_user_learning(user_id, f"Day discussion: {user_message}", response, user_name)
        return response

    # Document summary and analysis
    elif any(word in user_message for word in ["document", "summary", "summarize", "read", "uploaded", "file", "analyze"]):
        doc_name = None
        words = user_message.split()
        for i, word in enumerate(words):
            if word.lower() in ["document", "file", "summary"] and i + 1 < len(words):
                doc_name = " ".join(words[i+1:])
                break

        response = get_document_summary(user_id, doc_name)
        if user_id:
            save_user_learning(user_id, f"Question: {user_message}", response, user_name)
        return response

    # Tasks and progress
    elif any(word in user_message for word in ["task", "tasks", "progress", "what do i have", "my tasks", "what's assigned", "7"]):
        response = get_user_tasks(user_id)
        if user_id:
            save_user_learning(user_id, f"Question: {user_message}", response, user_name)
        return response

    # Staff on leave
    elif any(word in user_message for word in ["leave", "who is on leave", "staff on leave", "absent", "away"]):
        response = get_staff_on_leave()
        if user_id:
            save_user_learning(user_id, f"Question: {user_message}", response, user_name)
        return response

    # Annual returns (option 1)
    elif any(word in user_message for word in ["annual return", "return document", "filing", "1"]):
        response = f"""An annual return is a mandatory document that companies must file with the Business Registration Service (BRS) Kenya.

Key points about annual returns:

1. Must be filed within 30 days of the company's financial year-end
2. Contains information about directors, shareholders, and company activities
3. Requires payment of filing fees
4. Can be filed online through the BRS portal

To create an annual return in this system:

1. Navigate to the Documents section
2. Click "Create New Document"
3. Select "Annual Return" as the document type
4. Fill in the required company and director information
5. Review and submit

Would you like help with any specific part of the annual return process?"""
        if user_id:
            save_user_learning(user_id, f"Question: {user_message}", response, user_name)
        return response.strip()

    # Compliance (option 2)
    elif any(word in user_message for word in ["compliance", "requirement", "kenya", "kenyan", "2"]):
        response = f"""Kenyan companies have several compliance requirements:

Annual Requirements:

1. File annual returns with BRS Kenya
2. Submit financial statements
3. Pay annual registration fees
4. Update company information if changed

Ongoing Requirements:

1. Maintain proper company records
2. Keep director and shareholder information current
3. Comply with tax obligations
4. Follow corporate governance standards

Key Deadlines:

1. Annual returns: 30 days after financial year-end
2. Tax returns: As per KRA requirements
3. Company fees: Annual renewal required

This system helps you manage all these compliance requirements in one place. Would you like specific guidance on any compliance area?"""
        if user_id:
            save_user_learning(user_id, f"Question: {user_message}", response, user_name)
        return response.strip()

    # Staff management (option 3)
    elif any(word in user_message for word in ["staff", "employee", "add", "create", "3"]):
        response = f"""To add a new staff member to the system:

1. Go to the Staff section
2. Click "Add New Staff Member"
3. Enter their details:
   - Full name
   - Email address
   - Role (Admin, Accountant, Staff)
   - Department
4. Set their permissions based on role
5. Click Save

Staff roles in the system:

1. Super Admin: Full system access
2. Admin: Can manage companies and staff
3. Accountant: Can manage financial records
4. Staff: Limited access to assigned areas

Each staff member gets a unique login. You can manage their access and permissions from the Staff management page.

Need help with anything else?"""
        if user_id:
            save_user_learning(user_id, f"Question: {user_message}", response, user_name)
        return response.strip()

    # Deadlines (option 5)
    elif any(word in user_message for word in ["deadline", "date", "when", "filing", "5"]):
        response = f"""Important deadlines for Kenyan companies:

Annual Return Filing:

1. Due: 30 days after company's financial year-end
2. Late filing penalties apply

Tax Returns (KRA):

1. Individual income tax: June 30 annually
2. Corporate tax: As per company's financial year-end
3. VAT returns: Monthly or quarterly depending on registration

Company Registration Renewal:

1. Annual renewal required
2. Fees must be paid to maintain active status

Financial Statements:

1. Must be prepared within 4 months of financial year-end
2. Required for annual return filing

This system can help you track all these deadlines. Set reminders for important dates to ensure timely compliance.

Which deadline would you like more information about?"""
        if user_id:
            save_user_learning(user_id, f"Question: {user_message}", response, user_name)
        return response.strip()

    # Documents (option 4)
    elif any(word in user_message for word in ["document", "file", "upload", "manage", "4"]):
        response = f"""Document management in this system:

Creating Documents:

1. Annual returns
2. Financial statements
3. Board resolutions
4. Meeting minutes
5. Compliance reports

Managing Documents:

1. Go to Documents section
2. View all company documents
3. Upload new documents
4. Download existing documents
5. Track document status

Document Status:

1. Draft: Being prepared
2. Submitted: Sent to authorities
3. Approved: Accepted by authorities
4. Archived: Completed and stored

You can organize documents by type, date, or company. All documents are securely stored and easily retrievable.

What type of document would you like to work with?"""
        if user_id:
            save_user_learning(user_id, f"Question: {user_message}", response, user_name)
        return response.strip()

    # Company creation (option 6)
    elif any(word in user_message for word in ["company", "create", "register", "new", "6"]):
        response = f"""To create a new company in the system:

1. Navigate to Companies section
2. Click "Add New Company"
3. Enter company details:
   - Company name
   - Registration number
   - Business type
   - Directors' information
   - Shareholders' information
4. Set company risk level (Low, Medium, High)
5. Configure compliance requirements
6. Save

Company Information Needed:

1. Legal company name
2. BRS registration number
3. Physical address
4. Postal address
5. Contact details
6. Business classification

Once created, you can manage all company documents, staff assignments, and compliance tracking from the company profile.

Ready to create a company?"""
        if user_id:
            save_user_learning(user_id, f"Question: {user_message}", response, user_name)
        return response.strip()

    # Chat - Discuss your day or general topics (option 8)
    elif any(word in user_message for word in ["chat", "discuss", "day", "general", "talk", "8"]):
        response = generate_conversational_response(user_message, user_id, user_name)
        if user_id:
            save_user_learning(user_id, f"Chat: {user_message}", response, user_name)
        return response

    # Default response - check if question is outside knowledge base
    else:
        # Check if it's a specific question (not just random text)
        question_indicators = ["what", "how", "when", "where", "why", "who", "can", "is", "are", "do", "does", "?"]
        is_question = any(indicator in user_message for indicator in question_indicators)
        
        if is_question and len(user_message.split()) > 2:
            # Try to get answer from web search
            web_answer = generate_web_answer(user_message)
            
            if web_answer:
                # Successfully got answer from web
                response = f"""{web_answer}

I found this information from the web since it's outside my core knowledge base.

For topics I specialize in, ask me about:
1. Annual Returns - Creating and filing annual return documents
2. Compliance - Understanding Kenyan company compliance requirements
3. Staff Management - Adding and managing team members
4. Documents - Creating, uploading, and managing company documents
5. Deadlines - Tracking important filing and compliance deadlines
6. Companies - Setting up and managing company profiles
7. Tasks - View your assigned tasks and progress"""
            else:
                # Web search failed, provide Google link as fallback
                search_query = user_message.replace(" ", "+")
                google_url = f"https://www.google.com/search?q={search_query}"
                
                response = f"""I don't have specific information about that in my knowledge base, {user_name}. 

You can search for it on Google using this link:
{google_url}

Or try asking me about:
1. Annual Returns - Creating and filing annual return documents
2. Compliance - Understanding Kenyan company compliance requirements
3. Staff Management - Adding and managing team members
4. Documents - Creating, uploading, and managing company documents
5. Deadlines - Tracking important filing and compliance deadlines
6. Companies - Setting up and managing company profiles
7. Tasks - View your assigned tasks and progress
8. Math - Solve calculations (e.g., 1+1, 5*3, 10-2, 20/4)

What would you like to know?"""
        else:
            # Show menu for non-questions
            response = f"""I'm here to help, {user_name}! I didn't quite understand that. Here are the options I can help with:
1. Annual Returns - Creating and filing annual return documents
2. Compliance - Understanding Kenyan company compliance requirements
3. Staff Management - Adding and managing team members
4. Documents - Creating, uploading, and managing company documents
5. Deadlines - Tracking important filing and compliance deadlines
6. Companies - Setting up and managing company profiles
7. Tasks - View your assigned tasks and progress
8. Chat - Discuss your day or general topics

Just type the number or ask your question. I learn from every conversation we have!"""
        if user_id:
            save_user_learning(user_id, f"Question: {user_message}", response, user_name)
        return response




@api_view(["POST", "OPTIONS"])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
@throttle_classes([ChatRateThrottle])
def ai_chat(request):
    """
    AI Chat endpoint with streaming responses using local knowledge base.
    No external AI provider dependencies (OpenAI, Gemini, etc.).
    
    Request body:
    {
        "messages": [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}
        ]
    }
    
    Response: Server-Sent Events stream
    
    Authentication: TokenAuthentication only
    - Send token in Authorization header: "Authorization: Token <token>"
    - Token is generated during login and stored in localStorage on frontend
    """
    # Handle CORS preflight OPTIONS request
    if request.method == "OPTIONS":
        response = Response(status=200)
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        return response
    
    try:
        # Validate request
        if not request.data or "messages" not in request.data:
            return StreamingHttpResponse(
                iter([json.dumps({"error": {"message": "Missing 'messages' field"}})]),
                content_type="text/event-stream",
                status=400,
            )
        
        messages = request.data.get("messages", [])
        
        # Validate messages
        if not validate_messages(messages):
            return StreamingHttpResponse(
                iter([json.dumps({"error": {"message": "Invalid message format"}})]),
                content_type="text/event-stream",
                status=400,
            )
        
        # Log request
        logger.info(f"Chat request from user {request.user.id} with {len(messages)} messages")
        
        # Stream response with local knowledge base
        return StreamingHttpResponse(
            generate_local_response(messages, user=request.user),
            content_type="text/event-stream",
            status=200,
        )
    
    except Exception as e:
        logger.error(f"Error in ai_chat endpoint: {str(e)}")
        return StreamingHttpResponse(
            iter([json.dumps({"error": {"message": "Internal server error"}})]),
            content_type="text/event-stream",
            status=500,
        )
