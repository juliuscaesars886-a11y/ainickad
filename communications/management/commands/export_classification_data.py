"""
Django Management Command: Export Classification Data

Export classification logs to CSV or JSON for analysis.
Supports filtering by date range, confidence, type, and user.

Usage:
    python manage.py export_classification_data --format=csv
    python manage.py export_classification_data --format=json --output=data.json
    python manage.py export_classification_data --format=csv --days=7 --min-confidence=0.6
    python manage.py export_classification_data --format=csv --type=Navigation --user-id=123

**Validates: Requirements 13.4**
"""

import csv
import json
import os
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db.models import Q
from communications.models import ClassificationLog


class Command(BaseCommand):
    """
    Management command to export classification data for analysis.
    
    Supports:
    - CSV and JSON export formats
    - Filtering by date range, confidence, type, user
    - Custom output file paths
    - Statistics summary
    """
    
    help = 'Export classification data to CSV or JSON for analysis'
    
    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            '--format',
            type=str,
            choices=['csv', 'json'],
            required=True,
            help='Export format (csv or json)'
        )
        
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path (default: classification_data_YYYYMMDD.csv/json)'
        )
        
        parser.add_argument(
            '--days',
            type=int,
            help='Export logs from last N days (optional)'
        )
        
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date for export (YYYY-MM-DD format, optional)'
        )
        
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date for export (YYYY-MM-DD format, optional)'
        )
        
        parser.add_argument(
            '--min-confidence',
            type=float,
            help='Minimum confidence threshold (optional)'
        )
        
        parser.add_argument(
            '--max-confidence',
            type=float,
            help='Maximum confidence threshold (optional)'
        )
        
        parser.add_argument(
            '--type',
            type=str,
            choices=['Navigation', 'Feature_Guide', 'Company_Data', 'Kenya_Governance', 'Web_Search', 'Tip'],
            help='Filter by classification type (optional)'
        )
        
        parser.add_argument(
            '--user-id',
            type=int,
            help='Filter by user ID (optional)'
        )
        
        parser.add_argument(
            '--feedback',
            type=str,
            choices=['correct', 'incorrect', 'partial', 'none'],
            help='Filter by user feedback (optional)'
        )
        
        parser.add_argument(
            '--include-message',
            action='store_true',
            help='Include full message text in export (default: truncated to 100 chars)'
        )
        
        parser.add_argument(
            '--include-context',
            action='store_true',
            help='Include context data in export'
        )
        
        parser.add_argument(
            '--limit',
            type=int,
            help='Limit number of records to export (optional)'
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        try:
            self.verbosity = options['verbosity']
            self.export_format = options['format']
            self.output_file = options['output']
            self.days = options.get('days')
            self.start_date = options.get('start_date')
            self.end_date = options.get('end_date')
            self.min_confidence = options.get('min_confidence')
            self.max_confidence = options.get('max_confidence')
            self.classification_type = options.get('type')
            self.user_id = options.get('user_id')
            self.feedback = options.get('feedback')
            self.include_message = options['include_message']
            self.include_context = options['include_context']
            self.limit = options.get('limit')
            
            # Validate arguments
            self._validate_arguments()
            
            if self.verbosity >= 1:
                self.stdout.write(f'\nExporting classification data to {self.export_format.upper()}...')
            
            # Build query
            query = self._build_query()
            
            # Get logs
            logs = query.order_by('-timestamp')
            
            if self.limit:
                logs = logs[:self.limit]
            
            total_count = logs.count()
            
            if total_count == 0:
                self.stdout.write(self.style.WARNING('No logs found matching the criteria'))
                return
            
            if self.verbosity >= 1:
                self.stdout.write(f'Found {total_count:,} logs to export')
            
            # Show statistics
            if self.verbosity >= 1:
                self._show_statistics(logs)
            
            # Export data
            if self.export_format == 'csv':
                self._export_csv(logs)
            else:
                self._export_json(logs)
            
            # Success message
            if self.verbosity >= 1:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n✓ Successfully exported {total_count:,} logs to {self.output_file}'
                    )
                )
        
        except Exception as e:
            raise CommandError(f'Error exporting data: {str(e)}')
    
    def _validate_arguments(self):
        """Validate command line arguments."""
        # Validate confidence thresholds
        if self.min_confidence is not None:
            if self.min_confidence < 0.0 or self.min_confidence > 1.0:
                raise CommandError('Min confidence must be between 0.0 and 1.0')
        
        if self.max_confidence is not None:
            if self.max_confidence < 0.0 or self.max_confidence > 1.0:
                raise CommandError('Max confidence must be between 0.0 and 1.0')
        
        if self.min_confidence and self.max_confidence:
            if self.min_confidence > self.max_confidence:
                raise CommandError('Min confidence cannot be greater than max confidence')
        
        # Validate date arguments
        if self.days and (self.start_date or self.end_date):
            raise CommandError('Cannot use --days with --start-date or --end-date')
        
        if self.start_date:
            try:
                datetime.strptime(self.start_date, '%Y-%m-%d')
            except ValueError:
                raise CommandError('Start date must be in YYYY-MM-DD format')
        
        if self.end_date:
            try:
                datetime.strptime(self.end_date, '%Y-%m-%d')
            except ValueError:
                raise CommandError('End date must be in YYYY-MM-DD format')
        
        # Validate limit
        if self.limit is not None and self.limit <= 0:
            raise CommandError('Limit must be positive')
        
        # Generate output filename if not provided
        if not self.output_file:
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            extension = 'csv' if self.export_format == 'csv' else 'json'
            self.output_file = f'classification_data_{timestamp}.{extension}'
    
    def _build_query(self):
        """
        Build query based on filter arguments.
        
        Returns:
            QuerySet of ClassificationLog
        """
        query = ClassificationLog.objects.all()
        
        # Date filtering
        if self.days:
            cutoff_date = timezone.now() - timedelta(days=self.days)
            query = query.filter(timestamp__gte=cutoff_date)
            if self.verbosity >= 1:
                self.stdout.write(f'Filtering: last {self.days} days')
        
        if self.start_date:
            start_dt = timezone.make_aware(
                datetime.strptime(self.start_date, '%Y-%m-%d')
            )
            query = query.filter(timestamp__gte=start_dt)
            if self.verbosity >= 1:
                self.stdout.write(f'Filtering: from {self.start_date}')
        
        if self.end_date:
            end_dt = timezone.make_aware(
                datetime.strptime(self.end_date, '%Y-%m-%d')
            )
            # Add one day to include the entire end date
            end_dt = end_dt + timedelta(days=1)
            query = query.filter(timestamp__lt=end_dt)
            if self.verbosity >= 1:
                self.stdout.write(f'Filtering: until {self.end_date}')
        
        # Confidence filtering
        if self.min_confidence is not None:
            query = query.filter(confidence_score__gte=self.min_confidence)
            if self.verbosity >= 1:
                self.stdout.write(f'Filtering: confidence >= {self.min_confidence}')
        
        if self.max_confidence is not None:
            query = query.filter(confidence_score__lte=self.max_confidence)
            if self.verbosity >= 1:
                self.stdout.write(f'Filtering: confidence <= {self.max_confidence}')
        
        # Type filtering
        if self.classification_type:
            query = query.filter(classification_type=self.classification_type)
            if self.verbosity >= 1:
                self.stdout.write(f'Filtering: type = {self.classification_type}')
        
        # User filtering
        if self.user_id:
            query = query.filter(user_id=self.user_id)
            if self.verbosity >= 1:
                self.stdout.write(f'Filtering: user_id = {self.user_id}')
        
        # Feedback filtering
        if self.feedback:
            query = query.filter(user_feedback=self.feedback)
            if self.verbosity >= 1:
                self.stdout.write(f'Filtering: feedback = {self.feedback}')
        
        return query
    
    def _show_statistics(self, logs):
        """
        Show statistics about logs to be exported.
        
        Args:
            logs: QuerySet of logs to export
        """
        from django.db.models import Count, Avg
        
        self.stdout.write('\nSTATISTICS:')
        
        total_count = logs.count()
        
        # Type distribution
        type_counts = logs.values('classification_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        self.stdout.write('  Type distribution:')
        for item in type_counts:
            percentage = (item['count'] / total_count) * 100
            self.stdout.write(f'    {item["classification_type"]}: {item["count"]:,} ({percentage:.1f}%)')
        
        # Average confidence
        avg_confidence = logs.aggregate(Avg('confidence_score'))['confidence_score__avg']
        if avg_confidence:
            self.stdout.write(f'\n  Average confidence: {avg_confidence:.3f}')
        
        # Date range
        oldest_log = logs.order_by('timestamp').first()
        newest_log = logs.order_by('-timestamp').first()
        
        if oldest_log and newest_log:
            self.stdout.write('\n  Date range:')
            self.stdout.write(f'    From: {oldest_log.timestamp.strftime("%Y-%m-%d %H:%M:%S")}')
            self.stdout.write(f'    To: {newest_log.timestamp.strftime("%Y-%m-%d %H:%M:%S")}')
    
    def _export_csv(self, logs):
        """
        Export logs to CSV format.
        
        Args:
            logs: QuerySet of logs to export
        """
        if self.verbosity >= 1:
            self.stdout.write('\nExporting to CSV...')
        
        try:
            with open(self.output_file, 'w', newline='', encoding='utf-8') as csvfile:
                # Define CSV fields
                fieldnames = [
                    'id',
                    'timestamp',
                    'user_id',
                    'classification_type',
                    'confidence_score',
                    'processing_time_ms',
                    'user_feedback',
                ]
                
                if self.include_message:
                    fieldnames.append('message')
                else:
                    fieldnames.append('message_preview')
                
                if self.include_context:
                    fieldnames.append('context_data')
                
                # Add score columns for each type
                fieldnames.extend([
                    'score_navigation',
                    'score_feature_guide',
                    'score_company_data',
                    'score_kenya_governance',
                    'score_web_search',
                    'score_tip',
                ])
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                # Write rows
                for log in logs.iterator(chunk_size=1000):
                    row = {
                        'id': str(log.id),
                        'timestamp': log.timestamp.isoformat(),
                        'user_id': log.user_id,
                        'classification_type': log.classification_type,
                        'confidence_score': log.confidence_score,
                        'processing_time_ms': log.processing_time_ms,
                        'user_feedback': log.user_feedback,
                    }
                    
                    # Add message
                    if self.include_message:
                        row['message'] = log.message
                    else:
                        row['message_preview'] = log.message[:100] + '...' if len(log.message) > 100 else log.message
                    
                    # Add context
                    if self.include_context:
                        row['context_data'] = json.dumps(log.context_data)
                    
                    # Add individual scores
                    all_scores = log.all_scores or {}
                    row['score_navigation'] = all_scores.get('Navigation', '')
                    row['score_feature_guide'] = all_scores.get('Feature_Guide', '')
                    row['score_company_data'] = all_scores.get('Company_Data', '')
                    row['score_kenya_governance'] = all_scores.get('Kenya_Governance', '')
                    row['score_web_search'] = all_scores.get('Web_Search', '')
                    row['score_tip'] = all_scores.get('Tip', '')
                    
                    writer.writerow(row)
            
            # Show file size
            if self.verbosity >= 1:
                file_size = os.path.getsize(self.output_file)
                file_size_mb = file_size / (1024 * 1024)
                self.stdout.write(f'File size: {file_size_mb:.2f} MB')
        
        except Exception as e:
            raise CommandError(f'Error writing CSV file: {str(e)}')
    
    def _export_json(self, logs):
        """
        Export logs to JSON format.
        
        Args:
            logs: QuerySet of logs to export
        """
        if self.verbosity >= 1:
            self.stdout.write('\nExporting to JSON...')
        
        try:
            # Prepare export data
            export_data = {
                'metadata': {
                    'export_date': timezone.now().isoformat(),
                    'total_logs': logs.count(),
                    'filters': {
                        'days': self.days,
                        'start_date': self.start_date,
                        'end_date': self.end_date,
                        'min_confidence': self.min_confidence,
                        'max_confidence': self.max_confidence,
                        'classification_type': self.classification_type,
                        'user_id': self.user_id,
                        'feedback': self.feedback,
                    }
                },
                'logs': []
            }
            
            # Convert logs to dictionaries
            for log in logs.iterator(chunk_size=1000):
                log_data = {
                    'id': str(log.id),
                    'timestamp': log.timestamp.isoformat(),
                    'user_id': log.user_id,
                    'classification_type': log.classification_type,
                    'confidence_score': log.confidence_score,
                    'all_scores': log.all_scores,
                    'processing_time_ms': log.processing_time_ms,
                    'user_feedback': log.user_feedback,
                }
                
                # Add message
                if self.include_message:
                    log_data['message'] = log.message
                else:
                    log_data['message_preview'] = log.message[:100] + '...' if len(log.message) > 100 else log.message
                
                # Add context
                if self.include_context:
                    log_data['context_data'] = log.context_data
                
                export_data['logs'].append(log_data)
            
            # Write to file
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            # Show file size
            if self.verbosity >= 1:
                file_size = os.path.getsize(self.output_file)
                file_size_mb = file_size / (1024 * 1024)
                self.stdout.write(f'File size: {file_size_mb:.2f} MB')
        
        except Exception as e:
            raise CommandError(f'Error writing JSON file: {str(e)}')
