"""
Response Handlers for Message Classification

Implements specialized response handlers for each classification type.
Each handler generates appropriate responses based on the classification type.

Handlers:
- handle_staff_query: Staff information queries with database access
- handle_company_query: Company information queries with database access
- handle_document_query: Document queries with database access
- handle_task_query: Task queries with database access
- handle_template_query: Template queries with database access
- handle_deadline_query: Deadline queries including Kenyan statutory deadlines
- handle_math_query: Mathematical expression evaluation
- handle_navigation_query: Help finding features, UI navigation
- handle_greeting_query: Personalized greetings with user memory
- handle_kenya_governance_query: Compliance, regulations, procedures from knowledge base
- handle_fallback_query: Low confidence fallback with suggestions
"""

import logging
import os
from typing import Optional
from datetime import datetime, timedelta
from django.utils import timezone

from communications.classifier import (
    ClassificationResult,
    ClassificationContext,
    RESPONSE_LABELS,
    ClassificationType,
)
from communications.memory_helpers import (
    get_session_memory,
    update_session_memory,
    get_user_memory,
    store_conversation_topic,
)
from communications.permission_helpers import (
    get_permission_scope,
    apply_permission_filter,
)
from communications.math_evaluator import evaluate_math_expression
from communications.error_handlers import (
    handle_permission_error,
    handle_math_error,
    handle_database_error,
    handle_memory_error,
    handle_classification_error,
    handle_knowledge_base_error,
    handle_generic_error,
)

logger = logging.getLogger(__name__)


def _prepend_label(response: str, label: str) -> str:
    """Prepend response label to response text."""
    if not response:
        return response
    return f"{label} {response}"


def _read_knowledge_file(filename: str) -> Optional[str]:
    """
    Read content from knowledge base file.
    
    Args:
        filename: Name of the file in communications/knowledge/ directory
        
    Returns:
        File content as string, or None if file not found
    """
    try:
        # Get the directory where this file is located
        current_dir = os.path.dirname(os.path.abspath(__file__))
        knowledge_dir = os.path.join(current_dir, 'knowledge')
        file_path = os.path.join(knowledge_dir, filename)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        handle_knowledge_base_error(filename, e)
        return None


def _extract_kenya_compliance_section(query_lower: str) -> Optional[str]:
    """
    Extract relevant section from Kenya compliance knowledge base.
    
    Args:
        query_lower: User query in lowercase
        
    Returns:
        Relevant markdown content, or None if not found
    """
    content = _read_knowledge_file('KENYA_COMPLIANCE_2026.md')
    if not content:
        return None
    
    # Map keywords to sections
    section_keywords = {
        '14-day rule': '## 14-Day Rule',
        'director change': '## 14-Day Rule',
        'address change': '## 14-Day Rule',
        'annual return': '## Annual Returns (CR29)',
        'cr29': '## Annual Returns (CR29)',
        'agm': '## AGM Requirements',
        'annual general meeting': '## AGM Requirements',
        'beneficial ownership': '## Beneficial Ownership',
        'bof1': '## Beneficial Ownership',
        'tax compliance': '## Tax Compliance',
        'paye': '## Tax Compliance',
        'shif': '## Tax Compliance',
        'nssf': '## Tax Compliance',
        'vat': '## Tax Compliance',
        'etims': '## eTIMS Requirements',
        'statutory record': '## Statutory Record Keeping',
        'register': '## Statutory Record Keeping',
        'compliance calendar': '## Annual Compliance Calendar',
        'deadline': '## Annual Compliance Calendar',
        'penalty': '## Administrative Fines Table',
        'fine': '## Administrative Fines Table',
    }
    
    # Find matching section
    for keyword, section_header in section_keywords.items():
        if keyword in query_lower:
            # Extract section content
            start_idx = content.find(section_header)
            if start_idx != -1:
                # Find next section header
                next_section = content.find('\n## ', start_idx + len(section_header))
                if next_section != -1:
                    return content[start_idx:next_section].strip()
                else:
                    return content[start_idx:].strip()
    
    return None


def handle_staff_query(
    user_message: str,
    classification: ClassificationResult,
    context: Optional[ClassificationContext] = None
) -> str:
    """
    Handle staff queries - query Employee model with permission filtering.
    
    Args:
        user_message: Original user message
        classification: Classification result
        context: Optional classification context with user_id
    
    Returns:
        Response text with label prepended
    """
    label = RESPONSE_LABELS.get(ClassificationType.COMPANY_DATA.value, "")
    
    try:
        from staff.models import Staff
        from authentication.models import UserProfile
        
        if not context or not context.user_id:
            return _prepend_label(
                handle_permission_error(resource_type="staff information"),
                label
            )
        
        # Get permission scope
        permission_scope = get_permission_scope(context.user_id)
        
        # Query staff with permission filtering
        staff_queryset = Staff.objects.select_related('company', 'user').all()
        staff_queryset = apply_permission_filter(staff_queryset, context.user_id, permission_scope)
        
        # Filter active staff
        active_staff = staff_queryset.filter(employment_status='active')
        staff_count = active_staff.count()
        
        if staff_count == 0:
            response = "You don't have any active staff members in your accessible companies."
        else:
            # Build response with staff information
            response = f"**Staff Information**\n\n"
            response += f"You have **{staff_count} active staff member{'s' if staff_count != 1 else ''}**:\n\n"
            
            # Group by company if multiple companies
            companies = {}
            for staff in active_staff[:10]:  # Limit to 10 for readability
                company_name = staff.company.name
                if company_name not in companies:
                    companies[company_name] = []
                companies[company_name].append(staff)
            
            for company_name, staff_list in companies.items():
                if len(companies) > 1:
                    response += f"**{company_name}**\n"
                for staff in staff_list:
                    response += f"- **{staff.full_name}** - {staff.job_title}"
                    if staff.department:
                        response += f" ({staff.department})"
                    response += f" - {staff.email}\n"
                response += "\n"
            
            if staff_count > 10:
                response += f"_...and {staff_count - 10} more staff members_\n"
        
        # Store conversation topic
        try:
            store_conversation_topic(context.user_id, "staff information")
        except Exception as e:
            handle_memory_error("storing conversation topic", context.user_id, e)
        
        return _prepend_label(response, label)
        
    except Exception as e:
        error_msg = handle_database_error("staff query", "Staff", e)
        return _prepend_label(error_msg, label)


def handle_company_query(
    user_message: str,
    classification: ClassificationResult,
    context: Optional[ClassificationContext] = None
) -> str:
    """
    Handle company queries - query Company model with permission filtering.
    
    Args:
        user_message: Original user message
        classification: Classification result
        context: Optional classification context with user_id
    
    Returns:
        Response text with label prepended
    """
    label = RESPONSE_LABELS.get(ClassificationType.COMPANY_DATA.value, "")
    
    try:
        from companies.models import Company
        from authentication.models import UserProfile
        
        if not context or not context.user_id:
            return _prepend_label(
                handle_permission_error(resource_type="company information"),
                label
            )
        
        # Get user and their company
        try:
            user = UserProfile.objects.get(id=context.user_id)
        except UserProfile.DoesNotExist:
            return _prepend_label(
                handle_permission_error(context.user_id, "company information"),
                label
            )
        
        # Get permission scope
        permission_scope = get_permission_scope(context.user_id)
        
        # Query companies with permission filtering
        company_queryset = Company.objects.filter(is_active=True)
        company_queryset = apply_permission_filter(company_queryset, context.user_id, permission_scope)
        
        company_count = company_queryset.count()
        
        if company_count == 0:
            response = "You don't have access to any companies."
        elif company_count == 1:
            # Single company - show detailed information
            company = company_queryset.first()
            response = f"**{company.name}**\n\n"
            response += f"**Registration Details**\n"
            response += f"- Registration Number: {company.registration_number}\n"
            response += f"- Tax ID: {company.tax_id}\n"
            response += f"- Address: {company.address}\n"
            response += f"- Contact: {company.contact_email} | {company.contact_phone}\n\n"
            
            # Risk level
            response += f"**Risk Assessment**\n"
            response += f"- Risk Level: {company.get_risk_level_display()}\n"
            if company.risk_category:
                response += f"- Risk Category: {company.risk_category}\n"
            response += "\n"
            
            # Directors count
            directors_count = company.directors.filter(is_active=True, resignation_date__isnull=True).count()
            if directors_count > 0:
                response += f"**Board Composition**\n"
                response += f"- Active Directors: {directors_count}\n\n"
            
            # Documents count
            docs_count = company.documents.filter(is_archived=False).count()
            if docs_count > 0:
                response += f"**Documents**\n"
                response += f"- Total Documents: {docs_count}\n\n"
        else:
            # Multiple companies - show list
            response = f"**Your Companies**\n\n"
            response += f"You have access to **{company_count} companies**:\n\n"
            
            for company in company_queryset[:10]:
                response += f"**{company.name}**\n"
                response += f"- Registration: {company.registration_number}\n"
                response += f"- Risk Level: {company.get_risk_level_display()}\n\n"
            
            if company_count > 10:
                response += f"_...and {company_count - 10} more companies_\n"
        
        # Store conversation topic
        try:
            store_conversation_topic(context.user_id, "company information")
        except Exception as e:
            handle_memory_error("storing conversation topic", context.user_id, e)
        
        return _prepend_label(response, label)
        
    except Exception as e:
        error_msg = handle_database_error("company query", "Company", e)
        return _prepend_label(error_msg, label)


def handle_document_query(
    user_message: str,
    classification: ClassificationResult,
    context: Optional[ClassificationContext] = None
) -> str:
    """
    Handle document queries - query Document model with permission filtering.
    
    Args:
        user_message: Original user message
        classification: Classification result
        context: Optional classification context with user_id
    
    Returns:
        Response text with label prepended
    """
    label = RESPONSE_LABELS.get(ClassificationType.COMPANY_DATA.value, "")
    
    try:
        from documents.models import Document
        
        if not context or not context.user_id:
            return _prepend_label(
                handle_permission_error(resource_type="document information"),
                label
            )
        
        # Get permission scope
        permission_scope = get_permission_scope(context.user_id)
        
        # Query documents with permission filtering
        doc_queryset = Document.objects.select_related('company', 'uploaded_by').filter(is_archived=False)
        doc_queryset = apply_permission_filter(doc_queryset, context.user_id, permission_scope)
        
        doc_count = doc_queryset.count()
        
        if doc_count == 0:
            response = "You don't have any documents in your accessible companies."
        else:
            response = f"**Document Library**\n\n"
            response += f"You have **{doc_count} document{'s' if doc_count != 1 else ''}**:\n\n"
            
            # Group by category
            categories = {}
            for doc in doc_queryset[:15]:
                category = doc.get_category_display()
                if category not in categories:
                    categories[category] = []
                categories[category].append(doc)
            
            for category, docs in categories.items():
                response += f"**{category}** ({len(docs)})\n"
                for doc in docs[:5]:
                    response += f"- {doc.title} ({doc.file_extension}) - {doc.size_mb} MB\n"
                if len(docs) > 5:
                    response += f"  _...and {len(docs) - 5} more_\n"
                response += "\n"
            
            if doc_count > 15:
                response += f"_Total: {doc_count} documents across all categories_\n"
        
        # Store conversation topic
        try:
            store_conversation_topic(context.user_id, "documents")
        except Exception as e:
            handle_memory_error("storing conversation topic", context.user_id, e)
        
        return _prepend_label(response, label)
        
    except Exception as e:
        error_msg = handle_database_error("document query", "Document", e)
        return _prepend_label(error_msg, label)


def handle_task_query(
    user_message: str,
    classification: ClassificationResult,
    context: Optional[ClassificationContext] = None
) -> str:
    """
    Handle task queries - query Task model with permission filtering.
    
    Args:
        user_message: Original user message
        classification: Classification result
        context: Optional classification context with user_id
    
    Returns:
        Response text with label prepended
    """
    label = RESPONSE_LABELS.get(ClassificationType.COMPANY_DATA.value, "")
    
    try:
        from workflows.models import Task
        from authentication.models import UserProfile
        
        if not context or not context.user_id:
            return _prepend_label(
                handle_permission_error(resource_type="task information"),
                label
            )
        
        # Get user
        try:
            user = UserProfile.objects.get(id=context.user_id)
        except UserProfile.DoesNotExist:
            return _prepend_label(
                handle_permission_error(context.user_id, "task information"),
                label
            )
        
        # Get permission scope
        permission_scope = get_permission_scope(context.user_id)
        
        # Query tasks with permission filtering
        task_queryset = Task.objects.select_related('company', 'assignee', 'creator').all()
        task_queryset = apply_permission_filter(task_queryset, context.user_id, permission_scope)
        
        # Filter active tasks (not completed or cancelled)
        active_tasks = task_queryset.exclude(status__in=['completed', 'cancelled'])
        task_count = active_tasks.count()
        
        if task_count == 0:
            response = "You don't have any active tasks."
        else:
            response = f"**Your Tasks**\n\n"
            response += f"You have **{task_count} active task{'s' if task_count != 1 else ''}**:\n\n"
            
            # Group by priority
            urgent_tasks = active_tasks.filter(priority='urgent')
            high_tasks = active_tasks.filter(priority='high')
            medium_tasks = active_tasks.filter(priority='medium')
            low_tasks = active_tasks.filter(priority='low')
            
            if urgent_tasks.exists():
                response += f"**Urgent Priority** ({urgent_tasks.count()})\n"
                for task in urgent_tasks[:3]:
                    due_str = task.due_date.strftime('%d %b %Y')
                    overdue = " ⚠️ OVERDUE" if task.is_overdue else ""
                    response += f"- {task.title} - Due: {due_str}{overdue}\n"
                response += "\n"
            
            if high_tasks.exists():
                response += f"**High Priority** ({high_tasks.count()})\n"
                for task in high_tasks[:3]:
                    due_str = task.due_date.strftime('%d %b %Y')
                    overdue = " ⚠️ OVERDUE" if task.is_overdue else ""
                    response += f"- {task.title} - Due: {due_str}{overdue}\n"
                response += "\n"
            
            if medium_tasks.exists():
                response += f"**Medium Priority** ({medium_tasks.count()})\n"
                for task in medium_tasks[:2]:
                    due_str = task.due_date.strftime('%d %b %Y')
                    response += f"- {task.title} - Due: {due_str}\n"
                response += "\n"
            
            if low_tasks.exists():
                response += f"**Low Priority** ({low_tasks.count()})\n\n"
        
        # Store conversation topic
        try:
            store_conversation_topic(context.user_id, "tasks")
        except Exception as e:
            handle_memory_error("storing conversation topic", context.user_id, e)
        
        return _prepend_label(response, label)
        
    except Exception as e:
        error_msg = handle_database_error("task query", "Task", e)
        return _prepend_label(error_msg, label)


def handle_template_query(
    user_message: str,
    classification: ClassificationResult,
    context: Optional[ClassificationContext] = None
) -> str:
    """
    Handle template queries - query Template model.
    
    Args:
        user_message: Original user message
        classification: Classification result
        context: Optional classification context
    
    Returns:
        Response text with label prepended
    """
    label = RESPONSE_LABELS.get(ClassificationType.COMPANY_DATA.value, "")
    
    try:
        from documents.models import Template
        
        # Query active templates
        templates = Template.objects.filter(is_active=True).order_by('-usage_count')
        template_count = templates.count()
        
        if template_count == 0:
            response = "No document templates are currently available."
        else:
            response = f"**Document Templates**\n\n"
            response += f"We have **{template_count} template{'s' if template_count != 1 else ''}** available for your use.\n\n"
            
            # Group by category
            categories = {}
            for template in templates:
                category = template.get_category_display()
                if category not in categories:
                    categories[category] = []
                categories[category].append(template)
            
            # Present templates in prose format
            for category, tmpl_list in categories.items():
                response += f"**{category}**: "
                
                # Build list of template names
                template_names = []
                for tmpl in tmpl_list[:5]:
                    usage_info = f" (used {tmpl.usage_count} times)" if tmpl.usage_count > 0 else ""
                    template_names.append(f"{tmpl.name}{usage_info}")
                
                if len(tmpl_list) > 5:
                    response += ", ".join(template_names) + f", and {len(tmpl_list) - 5} more templates.\n\n"
                else:
                    response += ", ".join(template_names) + ".\n\n"
            
            response += "To use a template, navigate to the **Documents** section, click **Generate Document**, and select your desired template from the list."
        
        # Store conversation topic if context available
        if context and context.user_id:
            try:
                store_conversation_topic(context.user_id, "templates")
            except Exception as e:
                handle_memory_error("storing conversation topic", context.user_id, e)
        
        return _prepend_label(response, label)
        
    except Exception as e:
        error_msg = handle_database_error("template query", "Template", e)
        return _prepend_label(error_msg, label)


def handle_deadline_query(
    user_message: str,
    classification: ClassificationResult,
    context: Optional[ClassificationContext] = None
) -> str:
    """
    Handle deadline queries - include Kenyan statutory deadlines.
    
    Args:
        user_message: Original user message
        classification: Classification result
        context: Optional classification context
    
    Returns:
        Response text with label prepended
    """
    label = RESPONSE_LABELS.get(ClassificationType.KENYA_GOVERNANCE.value, "")
    
    try:
        query_lower = user_message.lower()
        
        # Check for specific deadline types
        if 'annual return' in query_lower or 'cr29' in query_lower:
            response = (
                "**Annual Return (CR29) Deadline**\n\n"
                "Your annual return is due **on or before your company's incorporation anniversary**.\n\n"
                "**Example**: If your company was incorporated on 15th March 2023, your CR29 is due by 15th March each year.\n\n"
                "**Fee**: KES 1,000\n"
                "**Penalty**: KES 500 per year of delay\n\n"
                "**Important**: File 30 days before the deadline to avoid last-minute issues."
            )
        elif 'agm' in query_lower or 'annual general meeting' in query_lower:
            response = (
                "**Annual General Meeting (AGM) Deadlines**\n\n"
                "**First AGM**: Within 18 months of incorporation\n"
                "**Subsequent AGMs**: Within 15 months of previous AGM\n"
                "**Financial Statements**: Within 6 months of financial year end\n\n"
                "**Notice Period**:\n"
                "- Private companies: 14 days minimum\n"
                "- Public companies: 21 days minimum\n\n"
                "**Penalty for non-compliance**: KES 50,000"
            )
        elif 'director' in query_lower and 'change' in query_lower:
            response = (
                "**Director Change Deadlines (14-Day Rule)**\n\n"
                "Starting 2026, all director changes must be filed **within 14 days** of occurrence:\n\n"
                "**Appointment (CR2)**:\n"
                "- File within 14 days of appointment\n"
                "- Fee: KES 650\n"
                "- Automatic penalty after 14 days\n\n"
                "**Resignation/Removal (CR8)**:\n"
                "- File within 14 days of resignation/removal\n"
                "- Fee: KES 650\n"
                "- Automatic penalty after 14 days"
            )
        elif 'tax' in query_lower or 'paye' in query_lower or 'vat' in query_lower:
            response = (
                "**Monthly Tax Deadlines**\n\n"
                "**PAYE (Pay As You Earn)**\n"
                "- Filing & Payment: 9th of following month\n"
                "- Penalty: KES 10,000 or 5% of tax due\n\n"
                "**SHIF (Social Health Insurance)**\n"
                "- Filing & Payment: 9th of following month\n"
                "- Rate: 2.75% of gross salary\n\n"
                "**NSSF (Pension)**\n"
                "- Filing & Payment: 15th of following month\n"
                "- Rate: 6% (3% employee + 3% employer)\n\n"
                "**VAT (if applicable)**\n"
                "- Filing & Payment: 20th of following month\n"
                "- Rate: 16%"
            )
        else:
            # General deadlines overview
            response = (
                "**Key Compliance Deadlines**\n\n"
                "**Monthly**\n"
                "- 9th: PAYE & SHIF filing and payment\n"
                "- 15th: NSSF filing and payment\n"
                "- 20th: VAT filing and payment (if applicable)\n\n"
                "**Event-Based (14-Day Rule)**\n"
                "- Director changes: Within 14 days\n"
                "- Address changes: Within 14 days\n"
                "- Share transfers: Within 30 days\n"
                "- Beneficial ownership changes: Within 30 days\n\n"
                "**Annual**\n"
                "- Annual Return (CR29): On incorporation anniversary\n"
                "- AGM: Within 15 months of previous AGM\n"
                "- Financial Statements: Within 6 months of financial year end\n\n"
                "Ask me about a specific deadline for more details!"
            )
        
        # Store conversation topic if context available
        if context and context.user_id:
            try:
                store_conversation_topic(context.user_id, "deadlines")
            except Exception as e:
                handle_memory_error("storing conversation topic", context.user_id, e)
        
        return _prepend_label(response, label)
        
    except Exception as e:
        error_msg = handle_generic_error("deadline query", e)
        return _prepend_label(error_msg, label)


def handle_math_query(
    user_message: str,
    classification: ClassificationResult,
    context: Optional[ClassificationContext] = None
) -> str:
    """
    Handle math queries - use evaluate_math_expression from math_evaluator.py.
    
    Args:
        user_message: Original user message
        classification: Classification result
        context: Optional classification context
    
    Returns:
        Response text with label prepended
    """
    label = RESPONSE_LABELS.get(ClassificationType.COMPANY_DATA.value, "")
    
    try:
        # Try to evaluate the expression
        result = evaluate_math_expression(user_message)
        
        if result is not None:
            response = f"**Calculation Result**\n\n{user_message} = **{result}**"
        else:
            response = (
                "I couldn't evaluate that mathematical expression. "
                "I can calculate expressions with:\n"
                "- Basic operators: +, -, *, /, %\n"
                "- Exponentiation: **\n"
                "- Parentheses for grouping\n\n"
                "Example: \"(5 + 3) * 2\" or \"100 / 3\""
            )
        
        return _prepend_label(response, label)
        
    except Exception as e:
        error_msg = handle_math_error(user_message, e)
        return _prepend_label(error_msg, label)


def handle_navigation_query(
    user_message: str,
    classification: ClassificationResult,
    context: Optional[ClassificationContext] = None
) -> str:
    """
    Handle navigation queries - step-by-step instructions, no menus.
    
    Args:
        user_message: Original user message
        classification: Classification result
        context: Optional classification context
    
    Returns:
        Response text with label prepended
    """
    label = RESPONSE_LABELS.get(ClassificationType.NAVIGATION.value, "")
    
    try:
        query_lower = user_message.lower()
        
        # Detect specific navigation requests
        if 'add' in query_lower and 'company' in query_lower:
            response = (
                "To add a new company to Ainick:\n\n"
                "Steps:\n"
                "1. Go to \"Companies\" in the main menu\n"
                "2. Click \"Add Company\" button\n"
                "3. Fill in company details (name, registration number, address)\n"
                "4. Add directors and their information\n"
                "5. Add shareholders with ownership percentages\n"
                "6. Add beneficial owners (10%+ ownership)\n"
                "7. Click \"Save Company\"\n\n"
                "The system will automatically set up compliance tracking. Would you like help with a specific part of this process?"
            )
        elif 'add' in query_lower and 'director' in query_lower:
            response = (
                "To add a director to a company:\n\n"
                "Steps:\n"
                "1. Go to \"Companies\" and select your company\n"
                "2. Click the \"Directors\" tab\n"
                "3. Click \"Add Director\"\n"
                "4. Enter director details (name, ID, KRA PIN, contact info)\n"
                "5. Upload ID copy\n"
                "6. Click \"Save\"\n\n"
                "Remember to file CR2 with BRS Kenya within 14 days (fee: KES 650). Need help with anything else?"
            )
        elif 'generate' in query_lower and 'document' in query_lower:
            response = (
                "To generate a document:\n\n"
                "Steps:\n"
                "1. Click \"Documents\" in the main menu\n"
                "2. Click \"Generate Document\"\n"
                "3. Select document type (AGM Notice, Board Minutes, etc.)\n"
                "4. Select the company\n"
                "5. Fill in required details\n"
                "6. Preview the document\n"
                "7. Click \"Save and Download\"\n\n"
                "You can then share or print the document. What type of document do you need?"
            )
        elif 'dashboard' in query_lower or 'home' in query_lower:
            response = (
                "To access the Dashboard:\n\n"
                "Options:\n"
                "1. Click \"Dashboard\" or \"Home\" in the main menu\n"
                "2. Click the Ainick logo from anywhere\n\n"
                "The Dashboard shows your companies, compliance deadlines, recent activities, and compliance health scores. What would you like to see?"
            )
        elif 'settings' in query_lower:
            response = (
                "To access Settings:\n\n"
                "Steps:\n"
                "1. Click your profile icon (top right)\n"
                "2. Select \"Settings\"\n\n"
                "You can configure company settings, user profile, system preferences, BRS/KRA integrations, offline mode, and notifications. What setting do you need to change?"
            )
        else:
            # General navigation overview
            response = (
                "The Ainick platform has several main sections:\n\n"
                "Main Sections:\n"
                "1. Dashboard - Overview of companies and deadlines\n"
                "2. Companies - Manage companies, directors, shareholders\n"
                "3. Documents - Generate and manage documents\n"
                "4. Employees - Manage team members\n"
                "5. Templates - Document templates library\n"
                "6. Settings - Configure account and preferences\n"
                "7. AI Assistant - Get compliance help\n"
                "8. Messages - Team communication\n"
                "9. Notifications - Compliance alerts\n\n"
                "What specific section would you like help with?"
            )
        
        # Store conversation topic if context available
        if context and context.user_id:
            try:
                store_conversation_topic(context.user_id, "navigation")
            except Exception as e:
                handle_memory_error("storing conversation topic", context.user_id, e)
        
        return _prepend_label(response, label)
        
    except Exception as e:
        error_msg = handle_generic_error("navigation query", e)
        return _prepend_label(error_msg, label)


def handle_greeting_query(
    user_message: str,
    classification: ClassificationResult,
    context: Optional[ClassificationContext] = None
) -> str:
    """
    Handle greeting queries - use preferred name from memory, provide proactive data.
    
    Args:
        user_message: Original user message
        classification: Classification result
        context: Optional classification context with user_id
    
    Returns:
        Response text with label prepended
    """
    label = RESPONSE_LABELS.get(ClassificationType.COMPANY_DATA.value, "")
    
    try:
        # Get user memory for personalization
        preferred_name = None
        if context and context.user_id:
            try:
                memory = get_user_memory(context.user_id)
                if memory and memory.preferred_name:
                    preferred_name = memory.preferred_name
            except Exception as e:
                handle_memory_error("retrieving user memory", context.user_id, e)
        
        # Build greeting
        greeting = "Hello"
        if preferred_name:
            greeting = f"Hello {preferred_name}"
        
        # Get time of day for contextual greeting
        current_hour = datetime.now().hour
        if 5 <= current_hour < 12:
            time_greeting = "Good morning"
        elif 12 <= current_hour < 17:
            time_greeting = "Good afternoon"
        else:
            time_greeting = "Good evening"
        
        if preferred_name:
            time_greeting = f"{time_greeting}, {preferred_name}"
        
        # Use time-based greeting if it's a time-specific greeting
        query_lower = user_message.lower()
        if 'morning' in query_lower or 'afternoon' in query_lower or 'evening' in query_lower:
            response = f"{time_greeting}! "
        else:
            response = f"{greeting}! "
        
        # Add proactive information
        response += "I'm your AI assistant for Kenyan corporate governance and compliance.\n\n"
        response += "I can help you with:\n"
        response += "1. BRS Kenya procedures and deadlines\n"
        response += "2. Company compliance requirements\n"
        response += "3. Tax obligations (PAYE, SHIF, NSSF, VAT)\n"
        response += "4. Document generation\n"
        response += "5. Navigating the system\n\n"
        response += "What would you like to know?"
        
        # Store conversation topic if context available
        if context and context.user_id:
            try:
                store_conversation_topic(context.user_id, "greeting")
            except Exception as e:
                handle_memory_error("storing conversation topic", context.user_id, e)
        
        return _prepend_label(response, label)
        
    except Exception as e:
        error_msg = handle_generic_error("greeting query", e)
        return _prepend_label(error_msg, label)


def handle_kenya_governance_query(
    user_message: str,
    classification: ClassificationResult,
    context: Optional[ClassificationContext] = None
) -> str:
    """
    Handle Kenya governance queries - query knowledge base files directly.
    
    CRITICAL: This handler must provide detailed answers from knowledge base,
    NOT numbered menus. This is the primary handler for compliance questions.
    
    Args:
        user_message: Original user message
        classification: Classification result
        context: Optional classification context
    
    Returns:
        Response text with label prepended
    """
    label = RESPONSE_LABELS.get(ClassificationType.KENYA_GOVERNANCE.value, "")
    
    try:
        query_lower = user_message.lower()
        
        # Try to extract relevant section from knowledge base
        section_content = _extract_kenya_compliance_section(query_lower)
        
        if section_content:
            # Found relevant section - return it
            response = section_content
            
            # Limit response length for readability (first 2000 chars)
            if len(response) > 2000:
                response = response[:2000] + "\n\n_...continued. Ask me for more specific details!_"
        else:
            # No specific section found - provide general guidance based on keywords
            if 'compliance' in query_lower or 'requirement' in query_lower:
                response = (
                    "Kenyan companies have several compliance requirements:\n\n"
                    "Annual Requirements:\n"
                    "1. File annual returns (CR29) with BRS Kenya on incorporation anniversary\n"
                    "2. Submit financial statements within 6 months of year-end\n"
                    "3. Hold AGM within required timeframes\n"
                    "4. Pay annual fees (KES 1,000 for CR29)\n\n"
                    "Ongoing Requirements:\n"
                    "1. Maintain proper company records and registers\n"
                    "2. File director/shareholder changes within 14 days\n"
                    "3. Keep beneficial ownership register updated\n"
                    "4. Comply with monthly tax obligations\n\n"
                    "Tax Deadlines:\n"
                    "1. PAYE & SHIF: 9th of following month\n"
                    "2. NSSF: 15th of following month\n"
                    "3. VAT: 20th of following month (if applicable)\n\n"
                    "Ask me about: Annual returns, BRS Kenya procedures, Tax compliance, 14-day rule, AGM requirements, or Beneficial ownership."
                )
            elif 'brs' in query_lower or 'business registration' in query_lower:
                response = (
                    "BRS Kenya is the official portal for company registration and filings:\n\n"
                    "Main Services:\n"
                    "1. Company registration (Private Ltd, LLP, Foreign)\n"
                    "2. Business name registration\n"
                    "3. Annual returns filing (CR29)\n"
                    "4. Beneficial ownership filing (BOF1)\n"
                    "5. Director changes (CR2/CR8)\n"
                    "6. Document retrieval (CR12 certificates)\n\n"
                    "Key Forms and Fees:\n"
                    "1. CR29 - Annual Return (KES 1,000)\n"
                    "2. CR2 - Add Director (KES 650)\n"
                    "3. CR8 - Remove Director (KES 650)\n"
                    "4. CR12 - Certificate of Good Standing (KES 650)\n"
                    "5. BOF1 - Beneficial Ownership (Free)\n\n"
                    "Portal: https://brs.go.ke\n\n"
                    "What specific BRS procedure do you need help with?"
                )
            elif 'how' in query_lower and ('use' in query_lower or 'navigate' in query_lower):
                response = (
                    "Ainick helps you manage Kenyan corporate governance:\n\n"
                    "Key Features:\n"
                    "1. Multi-company management dashboard\n"
                    "2. Automated compliance deadline tracking\n"
                    "3. Document generation with templates\n"
                    "4. Statutory register maintenance\n"
                    "5. Team collaboration tools\n"
                    "6. AI assistant for instant guidance\n\n"
                    "Compliance Tracking:\n"
                    "1. CR29 reminders (30 days before due)\n"
                    "2. 14-day countdown for director changes\n"
                    "3. AGM scheduling and tracking\n"
                    "4. Tax deadline alerts\n\n"
                    "What specific feature would you like to learn about?"
                )
            else:
                # General Kenya governance response
                response = (
                    "I can help with Kenyan corporate governance and compliance:\n\n"
                    "Companies Act 2015:\n"
                    "1. Company registration and formation\n"
                    "2. Director duties and responsibilities\n"
                    "3. AGM requirements and procedures\n"
                    "4. Shareholder rights and meetings\n\n"
                    "BRS Kenya Procedures:\n"
                    "1. Annual returns (CR29) - KES 1,000\n"
                    "2. Director forms (CR2, CR8) - KES 650\n"
                    "3. Beneficial ownership (BOF1) - Free\n"
                    "4. Share transfers (CR9) - KES 650\n\n"
                    "Tax Compliance:\n"
                    "1. PAYE, SHIF, NSSF monthly obligations\n"
                    "2. VAT registration and filing\n"
                    "3. eTIMS requirements\n\n"
                    "What specific compliance question do you have?"
                )
        
        # Store conversation topic if context available
        if context and context.user_id:
            try:
                store_conversation_topic(context.user_id, "kenya governance")
            except Exception as e:
                handle_memory_error("storing conversation topic", context.user_id, e)
        
        return _prepend_label(response, label)
        
    except Exception as e:
        error_msg = handle_generic_error("kenya governance query", e)
        return _prepend_label(error_msg, label)


def handle_fallback_query(
    user_message: str,
    classification: ClassificationResult,
    context: Optional[ClassificationContext] = None
) -> str:
    """
    Handle fallback queries - honest response, suggest alternatives, no menus.
    
    Args:
        user_message: Original user message
        classification: Classification result
        context: Optional classification context
    
    Returns:
        Response text with label prepended
    """
    label = RESPONSE_LABELS.get(ClassificationType.TIP.value, "")
    
    try:
        # Check message length
        if len(user_message.split()) < 3:
            response = (
                "Your message is quite short. Could you provide more details?\n\n"
                "Examples:\n"
                "1. How do I file an annual return?\n"
                "2. What are my upcoming deadlines?\n"
                "3. Show me my company information\n"
                "4. What is the 14-day rule?\n\n"
                "What would you like to know?"
            )
        else:
            response = (
                "I'm not entirely sure what you're asking. Here are some things I can help with:\n\n"
                "Compliance Help:\n"
                "1. Annual return requirements\n"
                "2. How to add a director\n"
                "3. Tax deadlines\n\n"
                "Company Information:\n"
                "1. Show your companies\n"
                "2. View your tasks\n"
                "3. Access your documents\n\n"
                "Navigation Help:\n"
                "1. How to generate a document\n"
                "2. How to add a company\n"
                "3. Where to find settings\n\n"
                "What would you like to know?"
            )
        
        return _prepend_label(response, label)
        
    except Exception as e:
        error_msg = handle_generic_error("fallback query", e)
        return _prepend_label(error_msg, label)


# Handler registry - maps classification types to handler functions
RESPONSE_HANDLERS = {
    ClassificationType.NAVIGATION.value: handle_navigation_query,
    ClassificationType.KENYA_GOVERNANCE.value: handle_kenya_governance_query,
    ClassificationType.COMPANY_DATA.value: handle_company_query,
    ClassificationType.FEATURE_GUIDE.value: handle_navigation_query,  # Feature guide uses navigation handler
    ClassificationType.WEB_SEARCH.value: handle_fallback_query,  # Web search not implemented yet
    ClassificationType.TIP.value: handle_fallback_query,  # Tip is the fallback
}


def get_handler(classification_type: str):
    """Get response handler for classification type."""
    return RESPONSE_HANDLERS.get(classification_type, handle_fallback_query)
