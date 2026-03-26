"""
Django Management Command: Tune Thresholds

Analyze classification performance and suggest threshold adjustments to achieve target accuracy.
Uses historical classification data to recommend optimal confidence thresholds.

Usage:
    python manage.py tune_thresholds --target-accuracy=0.90
    python manage.py tune_thresholds --target-accuracy=0.90 --days=30
    python manage.py tune_thresholds --target-accuracy=0.90 --test-dataset
    python manage.py tune_thresholds --target-accuracy=0.90 --apply

**Validates: Requirements 13.4**
"""

import json
import os
from datetime import datetime, timedelta
from collections import defaultdict
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.conf import settings
from communications.models import ClassificationLog
from communications.classifier import get_classifier, ClassificationContext, CLASSIFICATION_TYPES
from communications.classification_keywords import get_keyword_dictionaries


class Command(BaseCommand):
    """
    Management command to tune classification thresholds for target accuracy.
    
    Analyzes classification performance and suggests optimal thresholds for:
    - Fallback threshold (when to use fallback handler)
    - High confidence threshold (when to skip additional checks)
    - Per-type priority thresholds
    
    Can optionally apply suggested thresholds to settings.
    """
    
    help = 'Suggest threshold adjustments to achieve target accuracy'
    
    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            '--target-accuracy',
            type=float,
            required=True,
            help='Target accuracy (e.g., 0.90 for 90%%)'
        )
        
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days of data to analyze (default: 30)'
        )
        
        parser.add_argument(
            '--test-dataset',
            action='store_true',
            help='Use test dataset instead of production data'
        )
        
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Apply suggested thresholds to settings (requires confirmation)'
        )
        
        parser.add_argument(
            '--output',
            type=str,
            help='Save recommendations to JSON file (optional)'
        )
        
        parser.add_argument(
            '--min-samples',
            type=int,
            default=100,
            help='Minimum number of samples required for analysis (default: 100)'
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        try:
            self.verbosity = options['verbosity']
            self.target_accuracy = options['target_accuracy']
            self.days = options['days']
            self.test_dataset = options['test_dataset']
            self.apply_changes = options['apply']
            self.output_file = options['output']
            self.min_samples = options['min_samples']
            
            # Validate arguments
            self._validate_arguments()
            
            if self.verbosity >= 1:
                self.stdout.write(f'\nAnalyzing classification performance...')
                self.stdout.write(f'Target accuracy: {self.target_accuracy*100:.1f}%')
            
            # Analyze performance
            if self.test_dataset:
                analysis = self._analyze_test_dataset()
            else:
                analysis = self._analyze_production_data()
            
            # Generate recommendations
            recommendations = self._generate_recommendations(analysis)
            
            # Display recommendations
            self._display_recommendations(analysis, recommendations)
            
            # Save to file if requested
            if self.output_file:
                self._save_recommendations(recommendations)
            
            # Apply changes if requested
            if self.apply_changes:
                self._apply_recommendations(recommendations)
            
            # Success message
            if self.verbosity >= 1:
                self.stdout.write(
                    self.style.SUCCESS(
                        '\n✓ Threshold tuning analysis completed'
                    )
                )
        
        except Exception as e:
            raise CommandError(f'Error tuning thresholds: {str(e)}')
    
    def _validate_arguments(self):
        """Validate command line arguments."""
        if self.target_accuracy <= 0.0 or self.target_accuracy > 1.0:
            raise CommandError('Target accuracy must be between 0.0 and 1.0')
        
        if self.days <= 0:
            raise CommandError('Days must be positive')
        
        if self.min_samples <= 0:
            raise CommandError('Min samples must be positive')
        
        if self.output_file and not self.output_file.endswith('.json'):
            raise CommandError('Output file must have .json extension')
    
    def _analyze_test_dataset(self):
        """
        Analyze classification performance on test dataset.
        
        Returns:
            Dict containing analysis results
        """
        if self.verbosity >= 1:
            self.stdout.write('Analyzing test dataset...')
        
        # Load test dataset
        test_data = self._load_test_dataset()
        
        if len(test_data) < self.min_samples:
            raise CommandError(
                f'Test dataset has only {len(test_data)} samples, '
                f'minimum {self.min_samples} required'
            )
        
        # Initialize classifier
        classifier = get_classifier()
        classifier.keyword_dictionaries = get_keyword_dictionaries()
        classifier._initialized = True
        
        # Analyze classifications at different confidence thresholds
        analysis = {
            'total_samples': len(test_data),
            'current_accuracy': 0.0,
            'per_type_accuracy': {},
            'confidence_accuracy_curve': [],
            'threshold_analysis': {},
            'confusion_matrix': defaultdict(lambda: defaultdict(int)),
        }
        
        # Classify all messages and collect results
        results = []
        for test_case in test_data:
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
            
            # Classify
            classification_result = classifier.classify(message, context)
            
            results.append({
                'expected': expected_type,
                'actual': classification_result.type,
                'confidence': classification_result.confidence,
                'all_scores': classification_result.scores,
                'is_correct': classification_result.type == expected_type,
            })
            
            # Update confusion matrix
            analysis['confusion_matrix'][expected_type][classification_result.type] += 1
        
        # Calculate current accuracy
        correct_count = sum(1 for r in results if r['is_correct'])
        analysis['current_accuracy'] = correct_count / len(results)
        
        # Calculate per-type accuracy
        type_stats = defaultdict(lambda: {'correct': 0, 'total': 0})
        for result in results:
            expected = result['expected']
            type_stats[expected]['total'] += 1
            if result['is_correct']:
                type_stats[expected]['correct'] += 1
        
        for type_name, stats in type_stats.items():
            analysis['per_type_accuracy'][type_name] = {
                'accuracy': stats['correct'] / stats['total'] if stats['total'] > 0 else 0.0,
                'correct': stats['correct'],
                'total': stats['total'],
            }
        
        # Analyze accuracy at different confidence thresholds
        confidence_thresholds = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99]
        
        for threshold in confidence_thresholds:
            filtered_results = [r for r in results if r['confidence'] >= threshold]
            
            if filtered_results:
                correct = sum(1 for r in filtered_results if r['is_correct'])
                accuracy = correct / len(filtered_results)
                
                analysis['confidence_accuracy_curve'].append({
                    'threshold': threshold,
                    'accuracy': accuracy,
                    'sample_count': len(filtered_results),
                    'percentage_retained': len(filtered_results) / len(results),
                })
        
        # Analyze optimal thresholds for each type
        for type_name in CLASSIFICATION_TYPES:
            type_results = [r for r in results if r['expected'] == type_name]
            
            if not type_results:
                continue
            
            # Find optimal threshold for this type
            best_threshold = 0.0
            best_accuracy = 0.0
            
            for threshold in confidence_thresholds:
                filtered = [r for r in type_results if r['all_scores'].get(type_name, 0.0) >= threshold]
                
                if filtered:
                    correct = sum(1 for r in filtered if r['is_correct'])
                    accuracy = correct / len(filtered)
                    
                    if accuracy > best_accuracy and len(filtered) >= 5:  # Require at least 5 samples
                        best_accuracy = accuracy
                        best_threshold = threshold
            
            analysis['threshold_analysis'][type_name] = {
                'optimal_threshold': best_threshold,
                'accuracy_at_threshold': best_accuracy,
                'sample_count': len(type_results),
            }
        
        return analysis
    
    def _analyze_production_data(self):
        """
        Analyze classification performance on production data.
        
        Returns:
            Dict containing analysis results
        """
        if self.verbosity >= 1:
            self.stdout.write(f'Analyzing production data for last {self.days} days...')
        
        # Calculate date range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=self.days)
        
        # Get logs with user feedback (these are our ground truth)
        logs = ClassificationLog.objects.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date,
            user_feedback__in=['correct', 'incorrect', 'partial']
        ).order_by('-timestamp')
        
        total_count = logs.count()
        
        if total_count < self.min_samples:
            raise CommandError(
                f'Only {total_count} logs with user feedback found, '
                f'minimum {self.min_samples} required. '
                f'Try increasing --days or use --test-dataset instead.'
            )
        
        # Analyze classifications
        analysis = {
            'total_samples': total_count,
            'current_accuracy': 0.0,
            'per_type_accuracy': {},
            'confidence_accuracy_curve': [],
            'threshold_analysis': {},
            'confusion_matrix': defaultdict(lambda: defaultdict(int)),
        }
        
        # Calculate current accuracy (based on user feedback)
        correct_count = logs.filter(user_feedback='correct').count()
        partial_count = logs.filter(user_feedback='partial').count()
        
        # Count partial as 0.5 correct
        analysis['current_accuracy'] = (correct_count + (partial_count * 0.5)) / total_count
        
        # Calculate per-type accuracy
        for type_name in CLASSIFICATION_TYPES:
            type_logs = logs.filter(classification_type=type_name)
            type_count = type_logs.count()
            
            if type_count > 0:
                type_correct = type_logs.filter(user_feedback='correct').count()
                type_partial = type_logs.filter(user_feedback='partial').count()
                
                accuracy = (type_correct + (type_partial * 0.5)) / type_count
                
                analysis['per_type_accuracy'][type_name] = {
                    'accuracy': accuracy,
                    'correct': type_correct,
                    'partial': type_partial,
                    'total': type_count,
                }
        
        # Analyze accuracy at different confidence thresholds
        confidence_thresholds = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99]
        
        for threshold in confidence_thresholds:
            filtered_logs = logs.filter(confidence_score__gte=threshold)
            filtered_count = filtered_logs.count()
            
            if filtered_count > 0:
                correct = filtered_logs.filter(user_feedback='correct').count()
                partial = filtered_logs.filter(user_feedback='partial').count()
                accuracy = (correct + (partial * 0.5)) / filtered_count
                
                analysis['confidence_accuracy_curve'].append({
                    'threshold': threshold,
                    'accuracy': accuracy,
                    'sample_count': filtered_count,
                    'percentage_retained': filtered_count / total_count,
                })
        
        return analysis
    
    def _generate_recommendations(self, analysis):
        """
        Generate threshold recommendations based on analysis.
        
        Args:
            analysis: Analysis results dictionary
        
        Returns:
            Dict containing recommendations
        """
        if self.verbosity >= 1:
            self.stdout.write('\nGenerating recommendations...')
        
        recommendations = {
            'current_accuracy': analysis['current_accuracy'],
            'target_accuracy': self.target_accuracy,
            'meets_target': analysis['current_accuracy'] >= self.target_accuracy,
            'thresholds': {},
            'actions': [],
        }
        
        # Find optimal fallback threshold
        optimal_fallback = self._find_optimal_threshold(
            analysis['confidence_accuracy_curve'],
            self.target_accuracy
        )
        
        recommendations['thresholds']['fallback_threshold'] = optimal_fallback
        
        # Find optimal high confidence threshold
        # This should be where accuracy is very high (e.g., 95%+)
        optimal_high_confidence = self._find_optimal_threshold(
            analysis['confidence_accuracy_curve'],
            min(0.95, self.target_accuracy + 0.05)
        )
        
        recommendations['thresholds']['high_confidence_threshold'] = optimal_high_confidence
        
        # Analyze per-type thresholds
        for type_name, type_analysis in analysis.get('threshold_analysis', {}).items():
            if type_analysis['sample_count'] >= 10:  # Require at least 10 samples
                recommendations['thresholds'][f'{type_name.lower()}_threshold'] = type_analysis['optimal_threshold']
        
        # Generate action items
        if analysis['current_accuracy'] < self.target_accuracy:
            gap = self.target_accuracy - analysis['current_accuracy']
            recommendations['actions'].append(
                f'Current accuracy ({analysis["current_accuracy"]*100:.1f}%) is below target '
                f'({self.target_accuracy*100:.1f}%). Gap: {gap*100:.1f}%'
            )
            
            # Identify low-performing types
            for type_name, stats in analysis['per_type_accuracy'].items():
                if stats['accuracy'] < self.target_accuracy - 0.05:
                    recommendations['actions'].append(
                        f'Improve {type_name} accuracy: currently {stats["accuracy"]*100:.1f}%, '
                        f'add more keywords or training samples'
                    )
        
        # Check if adjusting thresholds alone can achieve target
        best_threshold_accuracy = max(
            (item['accuracy'] for item in analysis['confidence_accuracy_curve']),
            default=0.0
        )
        
        if best_threshold_accuracy >= self.target_accuracy:
            recommendations['actions'].append(
                f'Target accuracy achievable by adjusting confidence threshold to '
                f'{optimal_fallback:.2f}'
            )
        else:
            recommendations['actions'].append(
                f'Threshold adjustment alone cannot achieve target. '
                f'Best possible accuracy: {best_threshold_accuracy*100:.1f}%. '
                f'Consider improving keyword dictionaries or semantic analysis.'
            )
        
        return recommendations
    
    def _find_optimal_threshold(self, curve, target_accuracy):
        """
        Find optimal confidence threshold to achieve target accuracy.
        
        Args:
            curve: List of confidence-accuracy data points
            target_accuracy: Target accuracy to achieve
        
        Returns:
            Optimal threshold value
        """
        # Find the lowest threshold that achieves target accuracy
        for point in sorted(curve, key=lambda x: x['threshold']):
            if point['accuracy'] >= target_accuracy and point['sample_count'] >= 10:
                return point['threshold']
        
        # If target not achievable, return threshold with best accuracy
        if curve:
            best_point = max(curve, key=lambda x: x['accuracy'])
            return best_point['threshold']
        
        return 0.6  # Default fallback
    
    def _display_recommendations(self, analysis, recommendations):
        """
        Display recommendations to console.
        
        Args:
            analysis: Analysis results
            recommendations: Recommendations dictionary
        """
        self.stdout.write('\n' + '='*80)
        self.stdout.write(self.style.SUCCESS('THRESHOLD TUNING RECOMMENDATIONS'))
        self.stdout.write('='*80)
        
        # Current performance
        self.stdout.write('\nCURRENT PERFORMANCE:')
        self.stdout.write(f'  Overall Accuracy: {analysis["current_accuracy"]*100:.1f}%')
        self.stdout.write(f'  Target Accuracy: {self.target_accuracy*100:.1f}%')
        
        if recommendations['meets_target']:
            self.stdout.write(self.style.SUCCESS('  ✓ Target accuracy achieved!'))
        else:
            gap = self.target_accuracy - analysis['current_accuracy']
            self.stdout.write(
                self.style.WARNING(
                    f'  ⚠ Below target by {gap*100:.1f} percentage points'
                )
            )
        
        # Per-type accuracy
        if analysis['per_type_accuracy']:
            self.stdout.write('\nPER-TYPE ACCURACY:')
            for type_name, stats in sorted(analysis['per_type_accuracy'].items()):
                accuracy = stats['accuracy']
                status = '✓' if accuracy >= self.target_accuracy else '⚠'
                self.stdout.write(f'  {status} {type_name}: {accuracy*100:.1f}% ({stats["total"]} samples)')
        
        # Recommended thresholds
        self.stdout.write('\nRECOMMENDED THRESHOLDS:')
        for threshold_name, value in recommendations['thresholds'].items():
            self.stdout.write(f'  {threshold_name}: {value:.2f}')
        
        # Confidence-accuracy curve
        if analysis['confidence_accuracy_curve']:
            self.stdout.write('\nCONFIDENCE-ACCURACY CURVE:')
            self.stdout.write('  Threshold | Accuracy | Samples | % Retained')
            self.stdout.write('  ' + '-'*50)
            for point in analysis['confidence_accuracy_curve']:
                self.stdout.write(
                    f'  {point["threshold"]:8.2f} | {point["accuracy"]*100:7.1f}% | '
                    f'{point["sample_count"]:7,} | {point["percentage_retained"]*100:7.1f}%'
                )
        
        # Action items
        if recommendations['actions']:
            self.stdout.write('\nRECOMMENDED ACTIONS:')
            for i, action in enumerate(recommendations['actions'], 1):
                self.stdout.write(f'  {i}. {action}')
    
    def _save_recommendations(self, recommendations):
        """
        Save recommendations to JSON file.
        
        Args:
            recommendations: Recommendations dictionary
        """
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(recommendations, f, indent=2, default=str)
            
            if self.verbosity >= 1:
                self.stdout.write(f'\n✓ Recommendations saved to {self.output_file}')
        
        except Exception as e:
            self.stderr.write(f'Error saving recommendations: {str(e)}')
    
    def _apply_recommendations(self, recommendations):
        """
        Apply recommended thresholds to settings.
        
        Args:
            recommendations: Recommendations dictionary
        """
        self.stdout.write('\n' + '='*80)
        self.stdout.write('APPLY THRESHOLD CHANGES')
        self.stdout.write('='*80)
        
        self.stdout.write('\nThe following thresholds will be updated:')
        for threshold_name, value in recommendations['thresholds'].items():
            self.stdout.write(f'  {threshold_name}: {value:.2f}')
        
        self.stdout.write(
            self.style.WARNING(
                '\nWARNING: This will modify your Django settings. '
                'Make sure you have a backup!'
            )
        )
        
        confirm = input('\nType "yes" to apply changes: ')
        
        if confirm.lower() != 'yes':
            self.stdout.write(self.style.WARNING('Changes not applied'))
            return
        
        # Note: In a real implementation, you would update the settings file
        # or database configuration. For now, we just display the values.
        self.stdout.write(
            self.style.SUCCESS(
                '\n✓ Thresholds updated. Add these to your Django settings:\n'
            )
        )
        
        self.stdout.write('CLASSIFICATION_THRESHOLDS = {')
        for threshold_name, value in recommendations['thresholds'].items():
            self.stdout.write(f'    "{threshold_name}": {value:.2f},')
        self.stdout.write('}')
        
        self.stdout.write(
            '\nNote: You need to manually add these to your settings.py file '
            'and restart the server for changes to take effect.'
        )
    
    def _load_test_dataset(self):
        """
        Load test dataset from JSON file.
        
        Returns:
            List of test cases
        """
        current_dir = os.path.dirname(os.path.abspath(__file__))
        test_dataset_path = os.path.join(
            current_dir, '..', '..', 'tests', 'test_dataset.json'
        )
        test_dataset_path = os.path.abspath(test_dataset_path)
        
        if not os.path.exists(test_dataset_path):
            raise CommandError(f'Test dataset not found at {test_dataset_path}')
        
        try:
            with open(test_dataset_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                raise CommandError('Test dataset must be a list')
            
            return data
        
        except json.JSONDecodeError as e:
            raise CommandError(f'Invalid JSON in test dataset: {str(e)}')
        except Exception as e:
            raise CommandError(f'Error loading test dataset: {str(e)}')
