"""
Django Management Command: Reload Keywords

Reload keyword dictionaries without restarting the server.
Useful for updating classification keywords in production without downtime.

Usage:
    python manage.py reload_keywords
    python manage.py reload_keywords --verify

**Validates: Requirements 13.4**
"""

import logging
from django.core.management.base import BaseCommand, CommandError
from communications.classifier import get_classifier
from communications.classification_keywords import get_keyword_dictionaries

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Management command to reload keyword dictionaries without server restart.
    
    This command reloads the keyword dictionaries used by the classification
    system, allowing updates to classification rules without downtime.
    """
    
    help = 'Reload keyword dictionaries without restarting the server'
    
    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            '--verify',
            action='store_true',
            help='Verify keyword dictionaries after reload'
        )
        
        parser.add_argument(
            '--show-stats',
            action='store_true',
            help='Show statistics about loaded keywords'
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        try:
            self.verbosity = options['verbosity']
            self.verify = options['verify']
            self.show_stats = options['show_stats']
            
            if self.verbosity >= 1:
                self.stdout.write('Reloading keyword dictionaries...')
            
            # Get the classifier instance
            classifier = get_classifier()
            
            # Store old keyword count for comparison
            old_keyword_count = self._count_keywords(classifier.keyword_dictionaries)
            
            # Reload keyword dictionaries
            new_keywords = get_keyword_dictionaries()
            classifier.keyword_dictionaries = new_keywords
            
            # Count new keywords
            new_keyword_count = self._count_keywords(new_keywords)
            
            if self.verbosity >= 1:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Keywords reloaded successfully'
                    )
                )
                self.stdout.write(
                    f'  Old keyword count: {old_keyword_count}'
                )
                self.stdout.write(
                    f'  New keyword count: {new_keyword_count}'
                )
                
                if new_keyword_count > old_keyword_count:
                    diff = new_keyword_count - old_keyword_count
                    self.stdout.write(
                        self.style.SUCCESS(f'  Added {diff} new keywords')
                    )
                elif new_keyword_count < old_keyword_count:
                    diff = old_keyword_count - new_keyword_count
                    self.stdout.write(
                        self.style.WARNING(f'  Removed {diff} keywords')
                    )
                else:
                    self.stdout.write('  Keyword count unchanged')
            
            # Verify if requested
            if self.verify:
                self._verify_keywords(new_keywords)
            
            # Show statistics if requested
            if self.show_stats:
                self._show_statistics(new_keywords)
            
            if self.verbosity >= 1:
                self.stdout.write(
                    self.style.SUCCESS(
                        '\n✓ Keyword reload completed successfully'
                    )
                )
        
        except Exception as e:
            logger.error(f'Error reloading keywords: {str(e)}', exc_info=True)
            raise CommandError(f'Error reloading keywords: {str(e)}')
    
    def _count_keywords(self, keyword_dict: dict) -> int:
        """
        Count total keywords across all classification types.
        
        Args:
            keyword_dict: Dictionary of keywords by classification type
        
        Returns:
            Total keyword count
        """
        total = 0
        for type_name, keywords in keyword_dict.items():
            if isinstance(keywords, dict):
                total += len(keywords)
            elif isinstance(keywords, list):
                total += len(keywords)
        return total
    
    def _verify_keywords(self, keyword_dict: dict):
        """
        Verify keyword dictionaries are valid.
        
        Args:
            keyword_dict: Dictionary of keywords by classification type
        """
        if self.verbosity >= 1:
            self.stdout.write('\nVerifying keyword dictionaries...')
        
        from communications.classifier import CLASSIFICATION_TYPES
        
        errors = []
        warnings = []
        
        # Check all classification types are present
        for type_name in CLASSIFICATION_TYPES:
            if type_name not in keyword_dict:
                errors.append(f'Missing keywords for type: {type_name}')
            elif not keyword_dict[type_name]:
                warnings.append(f'Empty keywords for type: {type_name}')
        
        # Check for extra types
        for type_name in keyword_dict.keys():
            if type_name not in CLASSIFICATION_TYPES:
                warnings.append(f'Unknown classification type: {type_name}')
        
        # Check keyword format
        for type_name, keywords in keyword_dict.items():
            if not isinstance(keywords, (dict, list)):
                errors.append(
                    f'Invalid keyword format for {type_name}: '
                    f'expected dict or list, got {type(keywords).__name__}'
                )
        
        # Display results
        if errors:
            self.stdout.write(self.style.ERROR('\nERRORS:'))
            for error in errors:
                self.stdout.write(self.style.ERROR(f'  ✗ {error}'))
            raise CommandError('Keyword verification failed')
        
        if warnings:
            self.stdout.write(self.style.WARNING('\nWARNINGS:'))
            for warning in warnings:
                self.stdout.write(self.style.WARNING(f'  ⚠ {warning}'))
        
        if not errors and not warnings:
            self.stdout.write(
                self.style.SUCCESS('  ✓ All keyword dictionaries valid')
            )
    
    def _show_statistics(self, keyword_dict: dict):
        """
        Show statistics about loaded keywords.
        
        Args:
            keyword_dict: Dictionary of keywords by classification type
        """
        self.stdout.write('\nKEYWORD STATISTICS:')
        
        for type_name, keywords in keyword_dict.items():
            if isinstance(keywords, dict):
                count = len(keywords)
                
                # Calculate average weight if weights are present
                weights = []
                for keyword, weight in keywords.items():
                    if isinstance(weight, (int, float)):
                        weights.append(weight)
                
                avg_weight = sum(weights) / len(weights) if weights else 0
                
                self.stdout.write(
                    f'  {type_name}: {count} keywords '
                    f'(avg weight: {avg_weight:.2f})'
                )
                
                # Show top 3 keywords by weight
                if weights and self.verbosity >= 2:
                    sorted_keywords = sorted(
                        keywords.items(),
                        key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0,
                        reverse=True
                    )
                    self.stdout.write(f'    Top keywords:')
                    for keyword, weight in sorted_keywords[:3]:
                        self.stdout.write(f'      - "{keyword}" ({weight})')
            
            elif isinstance(keywords, list):
                count = len(keywords)
                self.stdout.write(f'  {type_name}: {count} keywords')
