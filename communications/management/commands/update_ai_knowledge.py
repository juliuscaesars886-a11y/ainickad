"""
Management command to invalidate AI knowledge cache
"""
from django.core.management.base import BaseCommand
from communications.ai_chat import invalidate_knowledge_cache


class Command(BaseCommand):
    help = 'Invalidate AI knowledge cache to force reload of knowledge base and context'
    
    def handle(self, *args, **options):
        """Execute the command"""
        invalidate_knowledge_cache()
        self.stdout.write(
            self.style.SUCCESS('✓ AI knowledge cache invalidated successfully')
        )
        self.stdout.write(
            'Knowledge base will be reloaded on next AI chat request'
        )
