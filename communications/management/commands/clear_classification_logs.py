"""
Django Management Command: Clear Classification Logs

Archive or delete old classification logs to manage database size.
Supports archiving to JSON file before deletion.

Usage:
    python manage.py clear_classification_logs --days=30
    python manage.py clear_classification_logs --days=30 --archive
    python manage.py clear_classification_logs --days=30 --archive --output=archive.json
    python manage.py clear_classification_logs --days=30 --dry-run

**Validates: Requirements 13.4**
"""

import json
import os
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db.models import Count
from communications.models import ClassificationLog


class Command(BaseCommand):
    """
    Management command to clear old classification logs.
    
    Supports:
    - Deleting logs older than specified days
    - Archiving logs to JSON before deletion
    - Dry-run mode to preview what would be deleted
    - Statistics about deleted logs
    """
    
    help = 'Clear old classification logs to manage database size'
    
    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete logs older than this many days (default: 30)'
        )
        
        parser.add_argument(
            '--archive',
            action='store_true',
            help='Archive logs to JSON file before deletion'
        )
        
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path for archive (default: classification_logs_archive_YYYYMMDD.json)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )
        
        parser.add_argument(
            '--min-confidence',
            type=float,
            help='Only delete logs with confidence below this threshold (optional)'
        )
        
        parser.add_argument(
            '--type',
            type=str,
            help='Only delete logs of specific classification type (optional)'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompt'
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        try:
            self.verbosity = options['verbosity']
            self.days = options['days']
            self.archive = options['archive']
            self.output_file = options['output']
            self.dry_run = options['dry_run']
            self.min_confidence = options['min_confidence']
            self.classification_type = options['type']
            self.force = options['force']
            
            # Validate arguments
            self._validate_arguments()
            
            # Calculate cutoff date
            cutoff_date = timezone.now() - timedelta(days=self.days)
            
            if self.verbosity >= 1:
                self.stdout.write(
                    f'\nClearing classification logs older than {self.days} days '
                    f'(before {cutoff_date.strftime("%Y-%m-%d %H:%M:%S")})'
                )
                if self.dry_run:
                    self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be deleted'))
            
            # Build query
            query = ClassificationLog.objects.filter(timestamp__lt=cutoff_date)
            
            if self.min_confidence is not None:
                query = query.filter(confidence_score__lt=self.min_confidence)
                if self.verbosity >= 1:
                    self.stdout.write(f'Filtering: confidence < {self.min_confidence}')
            
            if self.classification_type:
                query = query.filter(classification_type=self.classification_type)
                if self.verbosity >= 1:
                    self.stdout.write(f'Filtering: type = {self.classification_type}')
            
            # Get count and statistics
            total_count = query.count()
            
            if total_count == 0:
                self.stdout.write(
                    self.style.WARNING('\nNo logs found matching the criteria')
                )
                return
            
            # Show statistics
            self._show_statistics(query, total_count)
            
            # Confirm deletion unless forced or dry-run
            if not self.force and not self.dry_run:
                confirm = input(
                    f'\nAre you sure you want to delete {total_count:,} logs? '
                    f'This action cannot be undone. (yes/no): '
                )
                if confirm.lower() != 'yes':
                    self.stdout.write(self.style.WARNING('Operation cancelled'))
                    return
            
            # Archive if requested
            if self.archive and not self.dry_run:
                self._archive_logs(query)
            
            # Delete logs
            if not self.dry_run:
                deleted_count = self._delete_logs(query)
                
                if self.verbosity >= 1:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'\n✓ Successfully deleted {deleted_count:,} classification logs'
                        )
                    )
            else:
                if self.verbosity >= 1:
                    self.stdout.write(
                        self.style.WARNING(
                            f'\nDRY RUN: Would delete {total_count:,} logs'
                        )
                    )
        
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n\nOperation cancelled by user'))
        except Exception as e:
            raise CommandError(f'Error clearing logs: {str(e)}')
    
    def _validate_arguments(self):
        """Validate command line arguments."""
        if self.days <= 0:
            raise CommandError('Days must be positive')
        
        if self.min_confidence is not None:
            if self.min_confidence < 0.0 or self.min_confidence > 1.0:
                raise CommandError('Min confidence must be between 0.0 and 1.0')
        
        if self.classification_type:
            from communications.classifier import CLASSIFICATION_TYPES
            if self.classification_type not in CLASSIFICATION_TYPES:
                raise CommandError(
                    f'Invalid classification type: {self.classification_type}. '
                    f'Valid types: {", ".join(CLASSIFICATION_TYPES)}'
                )
        
        if self.output_file and not self.archive:
            raise CommandError('--output requires --archive')
    
    def _show_statistics(self, query, total_count: int):
        """
        Show statistics about logs to be deleted.
        
        Args:
            query: QuerySet of logs to be deleted
            total_count: Total number of logs
        """
        if self.verbosity >= 1:
            self.stdout.write('\nLOGS TO BE DELETED:')
            self.stdout.write(f'  Total: {total_count:,}')
            
            # Type distribution
            type_counts = query.values('classification_type').annotate(
                count=Count('id')
            ).order_by('-count')
            
            if type_counts:
                self.stdout.write('\n  By Type:')
                for item in type_counts:
                    percentage = (item['count'] / total_count) * 100
                    self.stdout.write(
                        f'    {item["classification_type"]}: {item["count"]:,} '
                        f'({percentage:.1f}%)'
                    )
            
            # Confidence distribution
            high_conf = query.filter(confidence_score__gt=0.8).count()
            medium_conf = query.filter(
                confidence_score__gte=0.6,
                confidence_score__lte=0.8
            ).count()
            low_conf = query.filter(confidence_score__lt=0.6).count()
            
            self.stdout.write('\n  By Confidence:')
            self.stdout.write(
                f'    High (>0.8): {high_conf:,} '
                f'({(high_conf/total_count)*100:.1f}%)'
            )
            self.stdout.write(
                f'    Medium (0.6-0.8): {medium_conf:,} '
                f'({(medium_conf/total_count)*100:.1f}%)'
            )
            self.stdout.write(
                f'    Low (<0.6): {low_conf:,} '
                f'({(low_conf/total_count)*100:.1f}%)'
            )
            
            # Date range
            oldest = query.order_by('timestamp').first()
            newest = query.order_by('-timestamp').first()
            
            if oldest and newest:
                self.stdout.write('\n  Date Range:')
                self.stdout.write(
                    f'    Oldest: {oldest.timestamp.strftime("%Y-%m-%d %H:%M:%S")}'
                )
                self.stdout.write(
                    f'    Newest: {newest.timestamp.strftime("%Y-%m-%d %H:%M:%S")}'
                )
    
    def _archive_logs(self, query):
        """
        Archive logs to JSON file before deletion.
        
        Args:
            query: QuerySet of logs to archive
        """
        if self.verbosity >= 1:
            self.stdout.write('\nArchiving logs to JSON...')
        
        # Generate output filename if not provided
        if not self.output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.output_file = f'classification_logs_archive_{timestamp}.json'
        
        # Prepare data for archiving
        logs_data = []
        
        for log in query.iterator(chunk_size=1000):
            logs_data.append({
                'id': str(log.id),
                'timestamp': log.timestamp.isoformat(),
                'user_id': log.user_id,
                'message': log.message,
                'classification_type': log.classification_type,
                'confidence_score': log.confidence_score,
                'all_scores': log.all_scores,
                'processing_time_ms': log.processing_time_ms,
                'user_feedback': log.user_feedback,
                'context_data': log.context_data,
            })
        
        # Write to file
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(
                    {
                        'archive_date': timezone.now().isoformat(),
                        'total_logs': len(logs_data),
                        'logs': logs_data
                    },
                    f,
                    indent=2,
                    default=str
                )
            
            if self.verbosity >= 1:
                file_size = os.path.getsize(self.output_file)
                file_size_mb = file_size / (1024 * 1024)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✓ Archived {len(logs_data):,} logs to {self.output_file} '
                        f'({file_size_mb:.2f} MB)'
                    )
                )
        
        except Exception as e:
            raise CommandError(f'Error archiving logs: {str(e)}')
    
    def _delete_logs(self, query):
        """
        Delete logs from database.
        
        Args:
            query: QuerySet of logs to delete
        
        Returns:
            Number of logs deleted
        """
        if self.verbosity >= 1:
            self.stdout.write('\nDeleting logs...')
        
        # Delete in batches to avoid memory issues
        deleted_count = 0
        batch_size = 1000
        
        while True:
            # Get batch of IDs
            batch_ids = list(
                query.values_list('id', flat=True)[:batch_size]
            )
            
            if not batch_ids:
                break
            
            # Delete batch
            batch_deleted, _ = ClassificationLog.objects.filter(
                id__in=batch_ids
            ).delete()
            
            deleted_count += batch_deleted
            
            if self.verbosity >= 2:
                self.stdout.write(f'  Deleted {deleted_count:,} logs...')
        
        return deleted_count
