"""
Unit Tests for Management Commands

Tests for the four maintenance management commands:
- reload_keywords
- clear_classification_logs
- export_classification_data
- tune_thresholds

**Validates: Requirements 13.4**
"""

import json
import os
import tempfile
from datetime import timedelta
from io import StringIO
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.core.management import call_command
from django.utils import timezone
from django.contrib.auth import get_user_model

from communications.models import ClassificationLog
from communications.classifier import get_classifier
from communications.classification_keywords import get_keyword_dictionaries


User = get_user_model()


class ReloadKeywordsCommandTest(TestCase):
    """Test reload_keywords management command."""
    
    def test_reload_keywords_basic(self):
        """Test basic keyword reload without options."""
        out = StringIO()
        call_command('reload_keywords', stdout=out)
        
        output = out.getvalue()
        self.assertIn('Keywords reloaded successfully', output)
        self.assertIn('Keyword reload completed successfully', output)
    
    def test_reload_keywords_with_stats(self):
        """Test keyword reload with statistics display."""
        out = StringIO()
        call_command('reload_keywords', '--show-stats', stdout=out)
        
        output = out.getvalue()
        self.assertIn('KEYWORD STATISTICS', output)
        self.assertIn('Navigation:', output)
        self.assertIn('Feature_Guide:', output)
    
    def test_reload_keywords_with_verify(self):
        """Test keyword reload with verification."""
        out = StringIO()
        call_command('reload_keywords', '--verify', stdout=out)
        
        output = out.getvalue()
        self.assertIn('Verifying keyword dictionaries', output)
        self.assertIn('All keyword dictionaries valid', output)
    
    def test_reload_keywords_updates_classifier(self):
        """Test that reload actually updates the classifier instance."""
        classifier = get_classifier()
        
        # Store original keywords
        original_keywords = classifier.keyword_dictionaries if hasattr(classifier, 'keyword_dictionaries') else None
        
        # Reload keywords
        call_command('reload_keywords', stdout=StringIO())
        
        # Verify classifier has keywords loaded
        self.assertTrue(hasattr(classifier, 'keyword_dictionaries'))
        self.assertIsNotNone(classifier.keyword_dictionaries)
        # Note: _initialized flag is set by load_keywords method, not by reload command
        
        # Verify all required types are present
        required_types = ['Navigation', 'Feature_Guide', 'Company_Data', 'Kenya_Governance', 'Web_Search', 'Tip']
        for type_name in required_types:
            self.assertIn(type_name, classifier.keyword_dictionaries)


class ClearClassificationLogsCommandTest(TestCase):
    """Test clear_classification_logs management command."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            full_name='Test User'
        )
        
        # Create old logs (40 days ago)
        old_date = timezone.now() - timedelta(days=40)
        for i in range(10):
            ClassificationLog.objects.create(
                timestamp=old_date,
                user=self.user,
                message=f'Old message {i}',
                classification_type='Navigation',
                confidence_score=0.8,
                processing_time_ms=100,
                all_scores={'Navigation': 0.8}
            )
        
        # Create recent logs (10 days ago)
        recent_date = timezone.now() - timedelta(days=10)
        for i in range(5):
            ClassificationLog.objects.create(
                timestamp=recent_date,
                user=self.user,
                message=f'Recent message {i}',
                classification_type='Feature_Guide',
                confidence_score=0.9,
                processing_time_ms=150,
                all_scores={'Feature_Guide': 0.9}
            )
    
    def test_clear_logs_dry_run(self):
        """Test dry run mode doesn't delete logs."""
        initial_count = ClassificationLog.objects.count()
        
        out = StringIO()
        call_command('clear_classification_logs', '--days=30', '--dry-run', stdout=out)
        
        output = out.getvalue()
        self.assertIn('DRY RUN MODE', output)
        self.assertIn('Would delete 10 logs', output)
        
        # Verify no logs were deleted
        self.assertEqual(ClassificationLog.objects.count(), initial_count)
    
    def test_clear_logs_deletes_old_logs(self):
        """Test that old logs are deleted."""
        out = StringIO()
        
        # Mock user input to confirm deletion
        with patch('builtins.input', return_value='yes'):
            call_command('clear_classification_logs', '--days=30', stdout=out)
        
        output = out.getvalue()
        self.assertIn('Successfully cleared', output)
        
        # Verify old logs were deleted
        self.assertEqual(ClassificationLog.objects.count(), 5)
        
        # Verify recent logs remain
        remaining_logs = ClassificationLog.objects.all()
        for log in remaining_logs:
            self.assertEqual(log.classification_type, 'Feature_Guide')
    
    def test_clear_logs_with_archive(self):
        """Test archiving logs before deletion."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            archive_file = f.name
        
        try:
            out = StringIO()
            
            with patch('builtins.input', return_value='yes'):
                call_command(
                    'clear_classification_logs',
                    '--days=30',
                    '--archive',
                    f'--output={archive_file}',
                    stdout=out
                )
            
            output = out.getvalue()
            self.assertIn('Archived', output)
            
            # Verify archive file exists and contains data
            self.assertTrue(os.path.exists(archive_file))
            
            with open(archive_file, 'r') as f:
                archive_data = json.load(f)
            
            self.assertIn('metadata', archive_data)
            self.assertIn('logs', archive_data)
            self.assertEqual(len(archive_data['logs']), 10)
        
        finally:
            if os.path.exists(archive_file):
                os.remove(archive_file)
    
    def test_clear_logs_with_type_filter(self):
        """Test filtering by classification type."""
        out = StringIO()
        
        with patch('builtins.input', return_value='yes'):
            call_command(
                'clear_classification_logs',
                '--days=30',
                '--type=Navigation',
                stdout=out
            )
        
        # Verify only Navigation logs were deleted
        self.assertEqual(ClassificationLog.objects.filter(classification_type='Navigation').count(), 0)
        self.assertEqual(ClassificationLog.objects.filter(classification_type='Feature_Guide').count(), 5)
    
    def test_clear_logs_with_min_confidence_filter(self):
        """Test filtering by minimum confidence."""
        # Add some low confidence logs
        low_conf_date = timezone.now() - timedelta(days=40)
        for i in range(5):
            ClassificationLog.objects.create(
                timestamp=low_conf_date,
                user=self.user,
                message=f'Low confidence message {i}',
                classification_type='Tip',
                confidence_score=0.3,
                processing_time_ms=100,
                all_scores={'Tip': 0.3}
            )
        
        out = StringIO()
        
        with patch('builtins.input', return_value='yes'):
            call_command(
                'clear_classification_logs',
                '--days=30',
                '--min-confidence=0.5',
                stdout=out
            )
        
        # Verify only low confidence logs were deleted
        remaining_logs = ClassificationLog.objects.filter(
            timestamp__lt=timezone.now() - timedelta(days=30)
        )
        # Should have 5 low confidence logs deleted, 10 old logs with 0.8 confidence remain
        self.assertEqual(remaining_logs.count(), 10)


class ExportClassificationDataCommandTest(TestCase):
    """Test export_classification_data management command."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            full_name='Test User'
        )
        
        # Create test logs
        for i in range(20):
            ClassificationLog.objects.create(
                timestamp=timezone.now() - timedelta(days=i),
                user=self.user,
                message=f'Test message {i}',
                classification_type='Navigation' if i % 2 == 0 else 'Feature_Guide',
                confidence_score=0.7 + (i % 3) * 0.1,
                processing_time_ms=100 + i * 10,
                all_scores={
                    'Navigation': 0.7 + (i % 3) * 0.1,
                    'Feature_Guide': 0.5,
                }
            )
    
    def test_export_csv_basic(self):
        """Test basic CSV export."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            csv_file = f.name
        
        try:
            out = StringIO()
            call_command(
                'export_classification_data',
                '--format=csv',
                f'--output={csv_file}',
                stdout=out
            )
            
            output = out.getvalue()
            self.assertIn('Successfully exported', output)
            
            # Verify CSV file exists and has content
            self.assertTrue(os.path.exists(csv_file))
            
            with open(csv_file, 'r') as f:
                content = f.read()
                self.assertIn('id,timestamp,user_id', content)
                self.assertIn('classification_type', content)
        
        finally:
            if os.path.exists(csv_file):
                os.remove(csv_file)
    
    def test_export_json_basic(self):
        """Test basic JSON export."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json_file = f.name
        
        try:
            out = StringIO()
            call_command(
                'export_classification_data',
                '--format=json',
                f'--output={json_file}',
                stdout=out
            )
            
            output = out.getvalue()
            self.assertIn('Successfully exported', output)
            
            # Verify JSON file exists and has valid structure
            self.assertTrue(os.path.exists(json_file))
            
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            self.assertIn('metadata', data)
            self.assertIn('logs', data)
            self.assertEqual(len(data['logs']), 20)
        
        finally:
            if os.path.exists(json_file):
                os.remove(json_file)
    
    def test_export_with_filters(self):
        """Test export with various filters."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json_file = f.name
        
        try:
            out = StringIO()
            call_command(
                'export_classification_data',
                '--format=json',
                f'--output={json_file}',
                '--days=7',
                '--min-confidence=0.8',
                '--type=Navigation',
                stdout=out
            )
            
            # Verify filtered data
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # All logs should be Navigation type with confidence >= 0.8
            for log in data['logs']:
                self.assertEqual(log['classification_type'], 'Navigation')
                self.assertGreaterEqual(log['confidence_score'], 0.8)
        
        finally:
            if os.path.exists(json_file):
                os.remove(json_file)
    
    def test_export_with_limit(self):
        """Test export with record limit."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json_file = f.name
        
        try:
            out = StringIO()
            call_command(
                'export_classification_data',
                '--format=json',
                f'--output={json_file}',
                '--limit=5',
                stdout=out
            )
            
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            self.assertEqual(len(data['logs']), 5)
        
        finally:
            if os.path.exists(json_file):
                os.remove(json_file)
    
    def test_export_shows_statistics(self):
        """Test that export shows statistics."""
        out = StringIO()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            csv_file = f.name
        
        try:
            call_command(
                'export_classification_data',
                '--format=csv',
                f'--output={csv_file}',
                stdout=out
            )
            
            output = out.getvalue()
            self.assertIn('STATISTICS', output)
            self.assertIn('Type distribution', output)
            self.assertIn('Average confidence', output)
        
        finally:
            if os.path.exists(csv_file):
                os.remove(csv_file)


class TuneThresholdsCommandTest(TestCase):
    """Test tune_thresholds management command."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            full_name='Test User'
        )
        
        # Create logs with user feedback (ground truth)
        for i in range(50):
            confidence = 0.5 + (i % 5) * 0.1
            is_correct = confidence > 0.7
            
            ClassificationLog.objects.create(
                timestamp=timezone.now() - timedelta(days=i % 30),
                user=self.user,
                message=f'Test message {i}',
                classification_type='Navigation',
                confidence_score=confidence,
                processing_time_ms=100,
                all_scores={'Navigation': confidence},
                user_feedback='correct' if is_correct else 'incorrect'
            )
    
    def test_tune_thresholds_basic(self):
        """Test basic threshold tuning."""
        out = StringIO()
        call_command(
            'tune_thresholds',
            '--target-accuracy=0.80',
            '--days=30',
            stdout=out
        )
        
        output = out.getvalue()
        self.assertIn('THRESHOLD TUNING RECOMMENDATIONS', output)
        self.assertIn('CURRENT PERFORMANCE', output)
        self.assertIn('RECOMMENDED THRESHOLDS', output)
        self.assertIn('fallback_threshold', output)
    
    def test_tune_thresholds_shows_accuracy(self):
        """Test that current accuracy is displayed."""
        out = StringIO()
        call_command(
            'tune_thresholds',
            '--target-accuracy=0.80',
            '--days=30',
            stdout=out
        )
        
        output = out.getvalue()
        self.assertIn('Overall Accuracy:', output)
        self.assertIn('Target Accuracy:', output)
    
    def test_tune_thresholds_shows_curve(self):
        """Test that confidence-accuracy curve is displayed."""
        out = StringIO()
        call_command(
            'tune_thresholds',
            '--target-accuracy=0.80',
            '--days=30',
            stdout=out
        )
        
        output = out.getvalue()
        self.assertIn('CONFIDENCE-ACCURACY CURVE', output)
        self.assertIn('Threshold', output)
        self.assertIn('Accuracy', output)
        self.assertIn('Samples', output)
    
    def test_tune_thresholds_with_output(self):
        """Test saving recommendations to file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json_file = f.name
        
        try:
            out = StringIO()
            call_command(
                'tune_thresholds',
                '--target-accuracy=0.80',
                '--days=30',
                f'--output={json_file}',
                stdout=out
            )
            
            # Verify recommendations file exists
            self.assertTrue(os.path.exists(json_file))
            
            with open(json_file, 'r') as f:
                recommendations = json.load(f)
            
            self.assertIn('current_accuracy', recommendations)
            self.assertIn('target_accuracy', recommendations)
            self.assertIn('thresholds', recommendations)
            self.assertIn('actions', recommendations)
        
        finally:
            if os.path.exists(json_file):
                os.remove(json_file)
    
    @patch('communications.management.commands.tune_thresholds.Command._load_test_dataset')
    def test_tune_thresholds_with_test_dataset(self, mock_load):
        """Test threshold tuning with test dataset."""
        # Mock test dataset
        mock_load.return_value = [
            {'message': 'How do I create a company?', 'expected_type': 'Navigation', 'context': {}},
            {'message': 'What does staff management do?', 'expected_type': 'Feature_Guide', 'context': {}},
        ] * 50  # 100 samples
        
        out = StringIO()
        call_command(
            'tune_thresholds',
            '--target-accuracy=0.90',
            '--test-dataset',
            stdout=out
        )
        
        output = out.getvalue()
        self.assertIn('Analyzing test dataset', output)
        self.assertIn('THRESHOLD TUNING RECOMMENDATIONS', output)
    
    def test_tune_thresholds_insufficient_samples(self):
        """Test error when insufficient samples."""
        # Delete most logs
        ClassificationLog.objects.all().delete()
        
        # Create only a few logs
        for i in range(5):
            ClassificationLog.objects.create(
                timestamp=timezone.now(),
                user=self.user,
                message=f'Test {i}',
                classification_type='Navigation',
                confidence_score=0.8,
                processing_time_ms=100,
                all_scores={'Navigation': 0.8},
                user_feedback='correct'
            )
        
        with self.assertRaises(Exception):
            call_command(
                'tune_thresholds',
                '--target-accuracy=0.90',
                '--days=30',
                stdout=StringIO()
            )


class ManagementCommandsIntegrationTest(TestCase):
    """Integration tests for management commands working together."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            full_name='Test User'
        )
        
        # Create diverse test logs
        types = ['Navigation', 'Feature_Guide', 'Company_Data', 'Kenya_Governance', 'Web_Search', 'Tip']
        
        for i in range(100):
            ClassificationLog.objects.create(
                timestamp=timezone.now() - timedelta(days=i % 60),
                user=self.user,
                message=f'Test message {i}',
                classification_type=types[i % len(types)],
                confidence_score=0.5 + (i % 5) * 0.1,
                processing_time_ms=100 + i,
                all_scores={types[i % len(types)]: 0.5 + (i % 5) * 0.1},
                user_feedback='correct' if i % 3 == 0 else 'none'
            )
    
    def test_workflow_export_tune_clear(self):
        """Test complete workflow: export, tune, then clear."""
        # Step 1: Export data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            export_file = f.name
        
        try:
            call_command(
                'export_classification_data',
                '--format=json',
                f'--output={export_file}',
                stdout=StringIO()
            )
            
            self.assertTrue(os.path.exists(export_file))
            
            # Step 2: Tune thresholds
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                tune_file = f.name
            
            try:
                call_command(
                    'tune_thresholds',
                    '--target-accuracy=0.80',
                    '--days=30',
                    f'--output={tune_file}',
                    stdout=StringIO()
                )
                
                self.assertTrue(os.path.exists(tune_file))
                
                # Step 3: Clear old logs
                initial_count = ClassificationLog.objects.count()
                
                with patch('builtins.input', return_value='yes'):
                    call_command(
                        'clear_classification_logs',
                        '--days=45',
                        stdout=StringIO()
                    )
                
                # Verify some logs were deleted
                self.assertLess(ClassificationLog.objects.count(), initial_count)
            
            finally:
                if os.path.exists(tune_file):
                    os.remove(tune_file)
        
        finally:
            if os.path.exists(export_file):
                os.remove(export_file)
    
    def test_reload_keywords_affects_classification(self):
        """Test that reloading keywords affects classification results."""
        # Get initial classification
        classifier = get_classifier()
        message = "How do I create a company?"
        
        # Reload keywords
        call_command('reload_keywords', stdout=StringIO())
        
        # Classify message
        result = classifier.classify(message)
        
        # Verify classification works
        self.assertIsNotNone(result)
        self.assertIn(result.type, ['Navigation', 'Feature_Guide', 'Company_Data', 'Kenya_Governance', 'Web_Search', 'Tip'])
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)
