"""
Django Management Command: Classification Metrics

Calculate accuracy metrics for the AI Message Classification System.
Provides detailed analysis of classification performance including:
- Overall accuracy on test dataset
- Per-type accuracy
- Confidence distribution
- Type distribution over time
- Confusion matrix

Usage:
    python manage.py classification_metrics --days=7
    python manage.py classification_metrics --test-dataset
    python manage.py classification_metrics --output=metrics.json

**Validates: Requirements 10.3-10.6**
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from collections import defaultdict, Counter

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.conf import settings

from communications.models import ClassificationLog
from communications.classifier import (
    get_classifier, ClassificationContext, CLASSIFICATION_TYPES
)
from communications.classification_keywords import get_keyword_dictionaries


class Command(BaseCommand):
    """
    Management command to calculate classification accuracy metrics.
    
    Provides comprehensive analysis of classification system performance
    including accuracy, confidence distribution, and confusion matrix.
    """
    
    help = 'Calculate accuracy metrics for AI message classification system'
    
    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to analyze (default: 7)'
        )
        
        parser.add_argument(
            '--test-dataset',
            action='store_true',
            help='Run accuracy analysis on test dataset'
        )
        
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path for JSON results (optional)'
        )
        
        parser.add_argument(
            '--format',
            choices=['console', 'json', 'csv'],
            default='console',
            help='Output format (default: console)'
        )
        
        parser.add_argument(
            '--min-confidence',
            type=float,
            default=0.0,
            help='Minimum confidence threshold for analysis (default: 0.0)'
        )
        
        parser.add_argument(
            '--user-id',
            type=int,
            help='Filter by specific user ID (optional)'
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        try:
            self.verbosity = options['verbosity']
            self.days = options['days']
            self.test_dataset = options['test_dataset']
            self.output_file = options['output']
            self.output_format = options['format']
            self.min_confidence = options['min_confidence']
            self.user_id = options['user_id']
            
            # Validate arguments
            self._validate_arguments()
            
            if self.test_dataset:
                # Run test dataset analysis
                results = self._analyze_test_dataset()
            else:
                # Run production data analysis
                results = self._analyze_production_data()
            
            # Output results
            self._output_results(results)
            
            # Success message
            if self.verbosity >= 1:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Classification metrics analysis completed successfully'
                    )
                )
        
        except Exception as e:
            raise CommandError(f'Error calculating metrics: {str(e)}')
    
    def _validate_arguments(self):
        """Validate command line arguments."""
        if self.days <= 0:
            raise CommandError('Days must be positive')
        
        if self.min_confidence < 0.0 or self.min_confidence > 1.0:
            raise CommandError('Min confidence must be between 0.0 and 1.0')
        
        if self.output_file and not self.output_file.endswith(('.json', '.csv')):
            raise CommandError('Output file must have .json or .csv extension')
    
    def _analyze_test_dataset(self) -> Dict:
        """
        Analyze classification accuracy on test dataset.
        
        Returns:
            Dict containing accuracy metrics and analysis results
        """
        if self.verbosity >= 1:
            self.stdout.write('Analyzing test dataset...')
        
        # Load test dataset
        test_data = self._load_test_dataset()
        
        if not test_data:
            raise CommandError('Test dataset is empty or not found')
        
        # Initialize classifier
        classifier = get_classifier()
        classifier.keyword_dictionaries = get_keyword_dictionaries()
        classifier._initialized = True
        
        # Run classifications
        results = {
            'total_messages': len(test_data),
            'correct_classifications': 0,
            'per_type_accuracy': {},
            'confusion_matrix': defaultdict(lambda: defaultdict(int)),
            'confidence_distribution': {
                'high_confidence': 0,      # > 0.8
                'medium_confidence': 0,    # 0.6-0.8
                'low_confidence': 0,       # < 0.6
            },
            'type_distribution': defaultdict(int),
            'processing_times': [],
            'detailed_results': [],
        }
        
        # Track per-type statistics
        type_stats = defaultdict(lambda: {'correct': 0, 'total': 0})
        
        for i, test_case in enumerate(test_data):
            if self.verbosity >= 2 and i % 20 == 0:
                self.stdout.write(f'Processing message {i+1}/{len(test_data)}...')
            
            message = test_case['message']
            expected_type = test_case['expected_type']
            context_data = test_case.get('context', {})
            
            # Create context if provided
            context = None
            if context_data:
                context = ClassificationContext(
                    user_id=context_data.get('user_id'),
                    user_role=context_data.get('user_role'),
                    company_name=context_data.get('company_name'),
                    company_id=context_data.get('company_id'),
                    conversation_history=context_data.get('conversation_history', [])
                )
            
            # Classify message
            start_time = timezone.now()
            classification_result = classifier.classify(message, context)
            end_time = timezone.now()
            
            processing_time = (end_time - start_time).total_seconds() * 1000
            results['processing_times'].append(processing_time)
            
            # Check accuracy
            is_correct = classification_result.type == expected_type
            if is_correct:
                results['correct_classifications'] += 1
                type_stats[expected_type]['correct'] += 1
            
            type_stats[expected_type]['total'] += 1
            
            # Update confusion matrix
            results['confusion_matrix'][expected_type][classification_result.type] += 1
            
            # Update confidence distribution
            confidence = classification_result.confidence
            if confidence > 0.8:
                results['confidence_distribution']['high_confidence'] += 1
            elif confidence >= 0.6:
                results['confidence_distribution']['medium_confidence'] += 1
            else:
                results['confidence_distribution']['low_confidence'] += 1
            
            # Update type distribution
            results['type_distribution'][classification_result.type] += 1
            
            # Store detailed result
            results['detailed_results'].append({
                'message': message,
                'expected_type': expected_type,
                'actual_type': classification_result.type,
                'confidence': confidence,
                'is_correct': is_correct,
                'processing_time_ms': processing_time,
                'all_scores': classification_result.scores
            })
        
        # Calculate per-type accuracy
        for type_name, stats in type_stats.items():
            if stats['total'] > 0:
                accuracy = stats['correct'] / stats['total']
                results['per_type_accuracy'][type_name] = {
                    'accuracy': accuracy,
                    'correct': stats['correct'],
                    'total': stats['total']
                }
        
        # Calculate overall accuracy
        results['overall_accuracy'] = results['correct_classifications'] / results['total_messages']
        
        # Calculate average processing time
        if results['processing_times']:
            results['avg_processing_time_ms'] = sum(results['processing_times']) / len(results['processing_times'])
            results['max_processing_time_ms'] = max(results['processing_times'])
            results['min_processing_time_ms'] = min(results['processing_times'])
        
        # Convert confidence distribution to percentages
        total = results['total_messages']
        results['confidence_distribution_pct'] = {
            'high_confidence': (results['confidence_distribution']['high_confidence'] / total) * 100,
            'medium_confidence': (results['confidence_distribution']['medium_confidence'] / total) * 100,
            'low_confidence': (results['confidence_distribution']['low_confidence'] / total) * 100,
        }
        
        # Convert type distribution to percentages
        results['type_distribution_pct'] = {
            type_name: (count / total) * 100
            for type_name, count in results['type_distribution'].items()
        }
        
        return results
    
    def _analyze_production_data(self) -> Dict:
        """
        Analyze classification metrics from production data.
        
        Returns:
            Dict containing production metrics and analysis results
        """
        if self.verbosity >= 1:
            self.stdout.write(f'Analyzing production data for last {self.days} days...')
        
        # Calculate date range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=self.days)
        
        # Build query
        query = Q(timestamp__gte=start_date, timestamp__lte=end_date)
        
        if self.min_confidence > 0.0:
            query &= Q(confidence_score__gte=self.min_confidence)
        
        if self.user_id:
            query &= Q(user_id=self.user_id)
        
        # Get classification logs
        logs = ClassificationLog.objects.filter(query).order_by('-timestamp')
        
        if not logs.exists():
            raise CommandError(f'No classification logs found for the specified criteria')
        
        # Initialize results
        results = {
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': self.days
            },
            'total_classifications': logs.count(),
            'confidence_distribution': {
                'high_confidence': 0,      # > 0.8
                'medium_confidence': 0,    # 0.6-0.8
                'low_confidence': 0,       # < 0.6
            },
            'type_distribution': defaultdict(int),
            'processing_times': {
                'avg_ms': 0,
                'max_ms': 0,
                'min_ms': 0,
                'p95_ms': 0,
                'p99_ms': 0,
            },
            'daily_breakdown': defaultdict(lambda: defaultdict(int)),
            'user_feedback_summary': defaultdict(int),
            'low_confidence_messages': [],
        }
        
        # Process logs
        processing_times = []
        daily_counts = defaultdict(int)
        
        for log in logs:
            # Confidence distribution
            confidence = log.confidence_score
            if confidence > 0.8:
                results['confidence_distribution']['high_confidence'] += 1
            elif confidence >= 0.6:
                results['confidence_distribution']['medium_confidence'] += 1
            else:
                results['confidence_distribution']['low_confidence'] += 1
                
                # Store low confidence messages for review
                if len(results['low_confidence_messages']) < 20:  # Limit to 20 examples
                    results['low_confidence_messages'].append({
                        'message': log.message[:100] + '...' if len(log.message) > 100 else log.message,
                        'type': log.classification_type,
                        'confidence': confidence,
                        'timestamp': log.timestamp.isoformat()
                    })
            
            # Type distribution
            results['type_distribution'][log.classification_type] += 1
            
            # Processing times
            if log.processing_time_ms:
                processing_times.append(log.processing_time_ms)
            
            # Daily breakdown
            date_key = log.timestamp.date().isoformat()
            results['daily_breakdown'][date_key][log.classification_type] += 1
            daily_counts[date_key] += 1
            
            # User feedback
            results['user_feedback_summary'][log.user_feedback] += 1
        
        # Calculate processing time statistics
        if processing_times:
            processing_times.sort()
            n = len(processing_times)
            results['processing_times']['avg_ms'] = sum(processing_times) / n
            results['processing_times']['max_ms'] = max(processing_times)
            results['processing_times']['min_ms'] = min(processing_times)
            results['processing_times']['p95_ms'] = processing_times[int(n * 0.95)] if n > 0 else 0
            results['processing_times']['p99_ms'] = processing_times[int(n * 0.99)] if n > 0 else 0
        
        # Convert confidence distribution to percentages
        total = results['total_classifications']
        results['confidence_distribution_pct'] = {
            'high_confidence': (results['confidence_distribution']['high_confidence'] / total) * 100,
            'medium_confidence': (results['confidence_distribution']['medium_confidence'] / total) * 100,
            'low_confidence': (results['confidence_distribution']['low_confidence'] / total) * 100,
        }
        
        # Convert type distribution to percentages
        results['type_distribution_pct'] = {
            type_name: (count / total) * 100
            for type_name, count in results['type_distribution'].items()
        }
        
        # Calculate daily averages
        if daily_counts:
            results['daily_average'] = sum(daily_counts.values()) / len(daily_counts)
        
        return results
    
    def _load_test_dataset(self) -> List[Dict]:
        """
        Load test dataset from JSON file.
        
        Returns:
            List of test cases with message, expected_type, and context
        """
        # Get the path relative to the current file
        current_dir = os.path.dirname(os.path.abspath(__file__))
        test_dataset_path = os.path.join(
            current_dir,
            '..',
            '..',
            'tests',
            'test_dataset.json'
        )
        test_dataset_path = os.path.abspath(test_dataset_path)
        
        if not os.path.exists(test_dataset_path):
            raise CommandError(f'Test dataset not found at {test_dataset_path}')
        
        try:
            with open(test_dataset_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                raise CommandError('Test dataset must be a list of test cases')
            
            # Validate test cases
            for i, test_case in enumerate(data):
                if not isinstance(test_case, dict):
                    raise CommandError(f'Test case {i} must be a dictionary')
                
                if 'message' not in test_case or 'expected_type' not in test_case:
                    raise CommandError(f'Test case {i} missing required fields')
                
                if test_case['expected_type'] not in CLASSIFICATION_TYPES:
                    raise CommandError(f'Test case {i} has invalid expected_type: {test_case["expected_type"]}')
            
            return data
        
        except json.JSONDecodeError as e:
            raise CommandError(f'Invalid JSON in test dataset: {str(e)}')
        except Exception as e:
            raise CommandError(f'Error loading test dataset: {str(e)}')
    
    def _output_results(self, results: Dict):
        """
        Output results in the specified format.
        
        Args:
            results: Analysis results dictionary
        """
        if self.output_format == 'json':
            self._output_json(results)
        elif self.output_format == 'csv':
            self._output_csv(results)
        else:
            self._output_console(results)
        
        # Save to file if specified
        if self.output_file:
            self._save_to_file(results)
    
    def _output_console(self, results: Dict):
        """Output results to console in human-readable format."""
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS('CLASSIFICATION METRICS ANALYSIS'))
        self.stdout.write('='*80)
        
        if self.test_dataset:
            self._output_test_dataset_console(results)
        else:
            self._output_production_console(results)
    
    def _output_test_dataset_console(self, results: Dict):
        """Output test dataset results to console."""
        # Overall accuracy
        accuracy = results['overall_accuracy'] * 100
        self.stdout.write(f'\nOVERALL ACCURACY: {accuracy:.1f}%')
        self.stdout.write(f'Correct Classifications: {results["correct_classifications"]}/{results["total_messages"]}')
        
        # Per-type accuracy
        self.stdout.write('\nPER-TYPE ACCURACY:')
        for type_name, stats in results['per_type_accuracy'].items():
            accuracy = stats['accuracy'] * 100
            self.stdout.write(f'  {type_name}: {accuracy:.1f}% ({stats["correct"]}/{stats["total"]})')
        
        # Confidence distribution
        self.stdout.write('\nCONFIDENCE DISTRIBUTION:')
        conf_dist = results['confidence_distribution_pct']
        self.stdout.write(f'  High (>0.8): {conf_dist["high_confidence"]:.1f}%')
        self.stdout.write(f'  Medium (0.6-0.8): {conf_dist["medium_confidence"]:.1f}%')
        self.stdout.write(f'  Low (<0.6): {conf_dist["low_confidence"]:.1f}%')
        
        # Type distribution
        self.stdout.write('\nTYPE DISTRIBUTION:')
        for type_name, percentage in results['type_distribution_pct'].items():
            count = results['type_distribution'][type_name]
            self.stdout.write(f'  {type_name}: {percentage:.1f}% ({count})')
        
        # Performance metrics
        if 'avg_processing_time_ms' in results:
            self.stdout.write('\nPERFORMANCE METRICS:')
            self.stdout.write(f'  Average processing time: {results["avg_processing_time_ms"]:.1f}ms')
            self.stdout.write(f'  Max processing time: {results["max_processing_time_ms"]:.1f}ms')
            self.stdout.write(f'  Min processing time: {results["min_processing_time_ms"]:.1f}ms')
        
        # Confusion matrix
        self.stdout.write('\nCONFUSION MATRIX:')
        self._output_confusion_matrix(results['confusion_matrix'])
        
        # Recommendations
        self._output_recommendations(results)
    
    def _output_production_console(self, results: Dict):
        """Output production data results to console."""
        # Date range and totals
        self.stdout.write(f'\nDATE RANGE: {results["date_range"]["start"][:10]} to {results["date_range"]["end"][:10]}')
        self.stdout.write(f'TOTAL CLASSIFICATIONS: {results["total_classifications"]:,}')
        self.stdout.write(f'DAILY AVERAGE: {results.get("daily_average", 0):.0f}')
        
        # Confidence distribution
        self.stdout.write('\nCONFIDENCE DISTRIBUTION:')
        conf_dist = results['confidence_distribution_pct']
        self.stdout.write(f'  High (>0.8): {conf_dist["high_confidence"]:.1f}%')
        self.stdout.write(f'  Medium (0.6-0.8): {conf_dist["medium_confidence"]:.1f}%')
        self.stdout.write(f'  Low (<0.6): {conf_dist["low_confidence"]:.1f}%')
        
        # Type distribution
        self.stdout.write('\nTYPE DISTRIBUTION:')
        for type_name, percentage in results['type_distribution_pct'].items():
            count = results['type_distribution'][type_name]
            self.stdout.write(f'  {type_name}: {percentage:.1f}% ({count:,})')
        
        # Performance metrics
        perf = results['processing_times']
        if perf['avg_ms'] > 0:
            self.stdout.write('\nPERFORMANCE METRICS:')
            self.stdout.write(f'  Average processing time: {perf["avg_ms"]:.1f}ms')
            self.stdout.write(f'  95th percentile: {perf["p95_ms"]:.1f}ms')
            self.stdout.write(f'  99th percentile: {perf["p99_ms"]:.1f}ms')
            self.stdout.write(f'  Max processing time: {perf["max_ms"]:.1f}ms')
        
        # User feedback
        self.stdout.write('\nUSER FEEDBACK:')
        for feedback, count in results['user_feedback_summary'].items():
            percentage = (count / results['total_classifications']) * 100
            self.stdout.write(f'  {feedback}: {percentage:.1f}% ({count:,})')
        
        # Low confidence examples
        if results['low_confidence_messages']:
            self.stdout.write('\nLOW CONFIDENCE EXAMPLES:')
            for example in results['low_confidence_messages'][:10]:
                self.stdout.write(f'  "{example["message"]}" -> {example["type"]} ({example["confidence"]:.2f})')
    
    def _output_confusion_matrix(self, confusion_matrix: Dict):
        """Output confusion matrix in readable format."""
        # Get all types that appear in the matrix
        all_types = set()
        for expected_type, actual_types in confusion_matrix.items():
            all_types.add(expected_type)
            all_types.update(actual_types.keys())
        
        all_types = sorted(all_types)
        
        if not all_types:
            self.stdout.write('  No data available')
            return
        
        # Print header
        header = '  Expected\\Actual'
        for type_name in all_types:
            header += f' {type_name[:8]:>8}'
        self.stdout.write(header)
        
        # Print rows
        for expected_type in all_types:
            row = f'  {expected_type[:12]:12}'
            for actual_type in all_types:
                count = confusion_matrix.get(expected_type, {}).get(actual_type, 0)
                row += f' {count:8}'
            self.stdout.write(row)
    
    def _output_recommendations(self, results: Dict):
        """Output recommendations based on analysis results."""
        self.stdout.write('\nRECOMMENDATIONS:')
        
        accuracy = results['overall_accuracy']
        
        if accuracy < 0.9:
            self.stdout.write('  • Overall accuracy below 90% - consider tuning keyword weights or thresholds')
        
        # Check per-type accuracy
        low_accuracy_types = []
        for type_name, stats in results['per_type_accuracy'].items():
            if stats['accuracy'] < 0.85:
                low_accuracy_types.append(type_name)
        
        if low_accuracy_types:
            self.stdout.write(f'  • Low accuracy types: {", ".join(low_accuracy_types)} - add more keywords or samples')
        
        # Check confidence distribution
        low_conf_pct = results['confidence_distribution_pct']['low_confidence']
        if low_conf_pct > 10:
            self.stdout.write(f'  • {low_conf_pct:.1f}% low confidence classifications - review semantic analysis')
        
        # Check processing time
        if 'avg_processing_time_ms' in results and results['avg_processing_time_ms'] > 200:
            self.stdout.write(f'  • Average processing time {results["avg_processing_time_ms"]:.1f}ms exceeds 200ms target')
        
        if accuracy >= 0.9:
            self.stdout.write('  ✓ Classification system performing well!')
    
    def _output_json(self, results: Dict):
        """Output results in JSON format."""
        # Convert defaultdict to regular dict for JSON serialization
        json_results = self._convert_for_json(results)
        
        json_output = json.dumps(json_results, indent=2, default=str)
        self.stdout.write(json_output)
    
    def _output_csv(self, results: Dict):
        """Output results in CSV format."""
        # For CSV, output key metrics in tabular format
        if self.test_dataset:
            self.stdout.write('Type,Accuracy,Correct,Total')
            for type_name, stats in results['per_type_accuracy'].items():
                self.stdout.write(f'{type_name},{stats["accuracy"]:.3f},{stats["correct"]},{stats["total"]}')
        else:
            self.stdout.write('Type,Count,Percentage')
            for type_name, count in results['type_distribution'].items():
                percentage = results['type_distribution_pct'][type_name]
                self.stdout.write(f'{type_name},{count},{percentage:.1f}')
    
    def _save_to_file(self, results: Dict):
        """Save results to specified output file."""
        try:
            json_results = self._convert_for_json(results)
            
            with open(self.output_file, 'w', encoding='utf-8') as f:
                if self.output_file.endswith('.json'):
                    json.dump(json_results, f, indent=2, default=str)
                elif self.output_file.endswith('.csv'):
                    # Write CSV format
                    if self.test_dataset:
                        f.write('Type,Accuracy,Correct,Total\n')
                        for type_name, stats in results['per_type_accuracy'].items():
                            f.write(f'{type_name},{stats["accuracy"]:.3f},{stats["correct"]},{stats["total"]}\n')
                    else:
                        f.write('Type,Count,Percentage\n')
                        for type_name, count in results['type_distribution'].items():
                            percentage = results['type_distribution_pct'][type_name]
                            f.write(f'{type_name},{count},{percentage:.1f}\n')
            
            if self.verbosity >= 1:
                self.stdout.write(f'Results saved to {self.output_file}')
        
        except Exception as e:
            self.stderr.write(f'Error saving to file: {str(e)}')
    
    def _convert_for_json(self, obj):
        """Convert defaultdict and other non-JSON types for serialization."""
        if isinstance(obj, defaultdict):
            return dict(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_for_json(item) for item in obj]
        else:
            return obj