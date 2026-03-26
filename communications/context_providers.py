"""
Dynamic Context Providers for AI Chat
Provides real-time app data and user-specific context to AI assistant
"""
import logging
from typing import Dict, Any, Optional
from django.apps import apps
from django.urls import get_resolver
from django.db.models import Count

logger = logging.getLogger(__name__)


def get_user_context(user) -> Dict[str, Any]:
    """
    Get user-specific context including role, company, and permissions
    
    Args:
        user: UserProfile instance
    
    Returns:
        Dictionary with user context data
    """
    try:
        return {
            'user_id': str(user.id),
            'user_email': user.email,
            'user_name': user.full_name or user.email,
            'user_role': user.get_role_display(),
            'user_company': user.company.name if user.company else None,
            'user_company_id': str(user.company.id) if user.company else None,
            'is_super_admin': user.is_super_admin,
            'is_admin': user.is_admin,
            'is_accountant': user.is_accountant,
            'can_approve': user.can_approve,
        }
    except Exception as e:
        logger.error(f"Error getting user context: {str(e)}")
        return {}


def get_company_context(user) -> Dict[str, Any]:
    """
    Get user's company data including directors, shareholders, documents
    
    Args:
        user: UserProfile instance
    
    Returns:
        Dictionary with company context data
    """
    if not user.company:
        return {
            'has_company': False,
            'message': 'User is not associated with any company'
        }
    
    try:
        company = user.company
        
        # Get counts
        directors_count = company.directors.filter(is_active=True).count()
        current_directors_count = company.directors.filter(
            is_active=True, 
            resignation_date__isnull=True
        ).count()
        
        # Get documents count if model exists
        documents_count = 0
        try:
            documents_count = company.documents.count()
        except AttributeError:
            pass
        
        # Get users count
        users_count = company.users.filter(is_active=True).count()
        
        return {
            'has_company': True,
            'company_name': company.name,
            'company_id': str(company.id),
            'registration_number': company.registration_number,
            'tax_id': company.tax_id,
            'contact_email': company.contact_email,
            'contact_phone': company.contact_phone,
            'risk_level': company.get_risk_level_display(),
            'risk_category': company.risk_category or 'Not specified',
            'is_active': company.is_active,
            'directors_count': directors_count,
            'current_directors_count': current_directors_count,
            'documents_count': documents_count,
            'users_count': users_count,
            'created_at': company.created_at.strftime('%Y-%m-%d'),
        }
    except Exception as e:
        logger.error(f"Error getting company context: {str(e)}")
        return {'has_company': False, 'error': str(e)}


def get_app_features_context() -> Dict[str, Any]:
    """
    Get current app features, models, and capabilities
    
    Returns:
        Dictionary with app features data
    """
    try:
        features = {
            'available_pages': [
                'Dashboard',
                'Companies',
                'Documents',
                'Templates',
                'Staff',
                'Tasks',
                'Settings',
                'AI Assistant',
                'Messages',
                'Notifications'
            ],
            'document_types': [
                'Annual Return',
                'Director Resignation',
                'AGM Notice',
                'Board Minutes',
                'Resolutions',
                'Financial Statements'
            ],
            'user_roles': [
                'Super Admin - Full system access',
                'Admin - Company management',
                'Accountant - Financial operations',
                'Staff - Basic access'
            ],
            'key_features': [
                'Company Management',
                'Director Management',
                'Document Generation',
                'Compliance Tracking',
                'User Management',
                'Internal Messaging',
                'Notifications System',
                'AI Assistant with BRS Knowledge'
            ]
        }
        
        # Get registered Django apps
        registered_apps = []
        for app_config in apps.get_app_configs():
            if not app_config.name.startswith('django.') and not app_config.name.startswith('rest_framework'):
                registered_apps.append({
                    'name': app_config.name,
                    'verbose_name': app_config.verbose_name,
                    'models': [model.__name__ for model in app_config.get_models()]
                })
        
        features['registered_apps'] = registered_apps
        
        return features
    except Exception as e:
        logger.error(f"Error getting app features context: {str(e)}")
        return {}


def get_recent_feature_updates() -> list:
    """
    Get recent feature updates from FeatureUpdate model
    
    Returns:
        List of recent feature updates
    """
    try:
        from .models import FeatureUpdate
        
        updates = FeatureUpdate.objects.filter(is_active=True).order_by('-date')[:5]
        
        return [
            {
                'date': update.date.strftime('%Y-%m-%d'),
                'feature': update.feature_name,
                'description': update.description,
                'category': update.get_category_display()
            }
            for update in updates
        ]
    except Exception as e:
        # FeatureUpdate model might not exist yet
        logger.debug(f"Could not load feature updates: {str(e)}")
        return [
            {'date': '2024-01-15', 'feature': 'Dynamic AI Context', 'description': 'AI now has real-time access to your company data'},
            {'date': '2024-01-10', 'feature': 'BRS Knowledge Base', 'description': 'Enhanced AI with Kenya BRS compliance knowledge'},
        ]


def get_statistics_context(user) -> Dict[str, Any]:
    """
    Get system-wide or company-specific statistics
    
    Args:
        user: UserProfile instance
    
    Returns:
        Dictionary with statistics
    """
    try:
        from companies.models import Company, Director
        from authentication.models import UserProfile
        
        stats = {}
        
        if user.is_super_admin:
            # System-wide stats for super admin
            stats['total_companies'] = Company.objects.filter(is_active=True).count()
            stats['total_users'] = UserProfile.objects.filter(is_active=True).count()
            stats['total_directors'] = Director.objects.filter(is_active=True).count()
        elif user.company:
            # Company-specific stats
            stats['company_users'] = user.company.users.filter(is_active=True).count()
            stats['company_directors'] = user.company.directors.filter(is_active=True).count()
        
        return stats
    except Exception as e:
        logger.error(f"Error getting statistics context: {str(e)}")
        return {}


def build_dynamic_context(user) -> str:
    """
    Build complete dynamic context string for AI system prompt
    
    Args:
        user: UserProfile instance
    
    Returns:
        Formatted context string
    """
    try:
        user_ctx = get_user_context(user)
        company_ctx = get_company_context(user)
        features_ctx = get_app_features_context()
        stats_ctx = get_statistics_context(user)
        recent_updates = get_recent_feature_updates()
        
        context_parts = [
            "\n\n--- CURRENT USER CONTEXT ---",
            f"Name: {user_ctx.get('user_name', 'Unknown')}",
            f"Role: {user_ctx.get('user_role', 'Unknown')}",
            f"Company: {user_ctx.get('user_company', 'No company assigned')}",
            f"Permissions: {'Can approve requests' if user_ctx.get('can_approve') else 'Standard user'}",
        ]
        
        if company_ctx.get('has_company'):
            context_parts.extend([
                "\n--- USER'S COMPANY DATA ---",
                f"Company Name: {company_ctx.get('company_name')}",
                f"Registration Number: {company_ctx.get('registration_number')}",
                f"Risk Level: {company_ctx.get('risk_level')}",
                f"Active Directors: {company_ctx.get('current_directors_count')}",
                f"Total Directors: {company_ctx.get('directors_count')}",
                f"Documents: {company_ctx.get('documents_count')}",
                f"Company Users: {company_ctx.get('users_count')}",
                f"Company Created: {company_ctx.get('created_at')}",
            ])
        
        if stats_ctx:
            context_parts.append("\n--- STATISTICS ---")
            for key, value in stats_ctx.items():
                context_parts.append(f"{key.replace('_', ' ').title()}: {value}")
        
        context_parts.extend([
            "\n--- AVAILABLE FEATURES ---",
            f"Pages: {', '.join(features_ctx.get('available_pages', []))}",
            f"Document Types: {', '.join(features_ctx.get('document_types', []))}",
        ])
        
        if recent_updates:
            context_parts.append("\n--- RECENT UPDATES ---")
            for update in recent_updates:
                context_parts.append(f"• {update['date']}: {update['feature']} - {update['description']}")
        
        context_parts.extend([
            "\n--- INSTRUCTIONS FOR AI ---",
            "When answering questions:",
            "- Reference the user's actual company data when relevant",
            "- Use real numbers from their company (e.g., 'You have X documents')",
            "- Consider the user's role and permissions",
            "- Mention features they have access to",
            "- Be specific about their company's compliance status",
            "- If they ask about 'my company', use the data above",
        ])
        
        return "\n".join(context_parts)
    
    except Exception as e:
        logger.error(f"Error building dynamic context: {str(e)}")
        return "\n\n--- DYNAMIC CONTEXT ERROR ---\nCould not load user-specific context."
