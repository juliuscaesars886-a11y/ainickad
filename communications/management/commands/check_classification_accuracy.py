"""
Django Management Command: Check Classification Accuracy

Monitors classification accuracy and sends alerts when it drops below threshold.
Run this command periodically via cron job or task scheduler.

Usage:
    python manage.py check_classification_accuracy --threshold=0.85 --days=1
    python manage.py check_classification_accuracy --threshold=0.85 --days=7 --email=admin@example.com

**Validates: Requirements 10.1-10.6**
"""

from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from communications.models import ClassificationLog


class Command(BaseCommand):
    """
    Management command to check classification accuracy and send alerts.
    
    Monitors:
    - Average confidence (proxy for accuracy)
    - Low confidence rate (< 0.6)
    - Slow classification rate (> 500ms)
    
    Sends alerts when thresholds are exceeded.
    """
    
    help = 'Check classification accuracy and send alerts if below threshold'
    
    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            '--threshold',
            type=float,
            default=0.85,
            help='Accuracy threshold (default: 0.85)'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='Number of days to analyze (default: 1)'
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email address to send alerts (optional, uses ADMIN_EMAIL from settings if not provided)'
        )
        parser.add_argument(
            '--low-confidence-threshold',
            type=float,
            default=0.15,
            help='Maximum acceptable rate of low confidence classifications (default: 0.15)'
        )
        parser.add_argument(
            '--slow-threshold',
            type=float,
            default=0.05,
            help='Maximum acceptable rate of slow classifications (default: 0.05)'
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        threshold = options['threshold']
        days = options['days']
        alert_email = options.get('email') or getattr(settings, 'ADMIN_EMAIL', None)
        low_confidence_threshold = options['low_confidence_threshold']
        slow_threshold = options['slow_threshold']
        
        self.stdout.write(f'\nChecking classification accuracy for last {days} days...')
        self.stdout.write(f'Accuracy threshold: {threshold}')
        self.stdout.write(f'Low confidence threshold: {low_confidence_threshold*100:.0f}%')
        self.stdout.write(f'Slow classification threshold: {slow_threshold*100:.0f}%\n')
        
        # Calculate date range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Get classification logs
        logs = ClassificationLog.objects.filter(
            timestamp__gte=start_date,
            timestamp__lte=end_date
        )
        
        total_count = logs.count()
        
        if total_count == 0:
            self.stdout.write(self.style.WARNING('No classifications found in the specified period'))
            return
        
        # Calculate metrics
        avg_confidence = sum(log.confidence_score for log in logs) / total_count
        
        # Count low confidence classifications
        low_confidence_count = logs.filter(confidence_score__lt=0.6).count()
        low_confidence_rate = low_confidence_count / total_count
        
        # Count slow classifications
        slow_count = logs.filter(processing_time_ms__gt=500).count()
        slow_rate = slow_count / total_count
        
        # Calculate average processing time
        avg_processing_time = sum(log.processing_time_ms for log in logs) / total_count
        
        # Display current metrics
        self.stdout.write('CURRENT METRICS:')
        self.stdout.write(f'  Total Classifications: {total_count:,}')
        self.stdout.write(f'  Average Confidence: {avg_confidence:.3f}')
        self.stdout.write(f'  Low Confidence Rate: {low_confidence_rate*100:.1f}% ({low_confidence_count:,})')
        self.stdout.write(f'  Slow Classification Rate: {slow_rate*100:.1f}% ({slow_count:,})')
        self.stdout.write(f'  Average Processing Time: {avg_processing_time:.1f}ms\n')
        
        # Check if alert should be sent
        should_alert = False
        alert_reasons = []
        
        if avg_confidence < threshold:
            should_alert = True
            alert_reasons.append(
                f"Average confidence ({avg_confidence:.3f}) below threshold ({threshold})"
            )
        
        if low_confidence_rate > low_confidence_threshold:
            should_alert = True
            alert_reasons.append(
                f"High rate of low confidence classifications: {low_confidence_rate*100:.1f}% "
                f"(threshold: {low_confidence_threshold*100:.0f}%)"
            )
        
        if slow_rate > slow_threshold:
            should_alert = True
            alert_reasons.append(
                f"High rate of slow classifications (>500ms): {slow_rate*100:.1f}% "
                f"(threshold: {slow_threshold*100:.0f}%)"
            )
        
        # Send alert if needed
        if should_alert:
            self.stdout.write(self.style.ERROR('\n⚠️  ALERT: Classification quality issues detected\n'))
            
            for reason in alert_reasons:
                self.stdout.write(self.style.WARNING(f'  ❌ {reason}'))
            
            # Get examples of low confidence messages
            low_confidence_examples = logs.filter(
                confidence_score__lt=0.6
            ).order_by('confidence_score')[:5]
            
            if low_confidence_examples:
                self.stdout.write('\nLOW CONFIDENCE EXAMPLES:')
                for log in low_confidence_examples:
                    message_preview = log.message[:60] + '...' if len(log.message) > 60 else log.message
                    self.stdout.write(
                        f'  • "{message_preview}" -> {log.classification_type} '
                        f'({log.confidence_score:.2f})'
                    )
            
            # Send email alert if configured
            if alert_email:
                self._send_email_alert(
                    alert_email,
                    alert_reasons,
                    {
                        'total_count': total_count,
                        'avg_confidence': avg_confidence,
                        'low_confidence_rate': low_confidence_rate,
                        'low_confidence_count': low_confidence_count,
                        'slow_rate': slow_rate,
                        'slow_count': slow_count,
                        'avg_processing_time': avg_processing_time,
                        'days': days,
                        'low_confidence_examples': [
                            {
                                'message': log.message[:100],
                                'type': log.classification_type,
                                'confidence': log.confidence_score
                            }
                            for log in low_confidence_examples
                        ]
                    }
                )
                self.stdout.write(f'\n✉️  Alert email sent to {alert_email}')
            else:
                self.stdout.write(
                    self.style.WARNING(
                        '\n⚠️  No email configured. Set --email or ADMIN_EMAIL in settings to receive alerts.'
                    )
                )
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ Classification system performing well!\n'))
            self.stdout.write(f'  ✓ Average confidence: {avg_confidence:.3f} (threshold: {threshold})')
            self.stdout.write(f'  ✓ Low confidence rate: {low_confidence_rate*100:.1f}% (threshold: {low_confidence_threshold*100:.0f}%)')
            self.stdout.write(f'  ✓ Slow classification rate: {slow_rate*100:.1f}% (threshold: {slow_threshold*100:.0f}%)')
    
    def _send_email_alert(self, email, reasons, metrics):
        """
        Send email alert for classification issues.
        
        Args:
            email: Email address to send alert to
            reasons: List of alert reasons
            metrics: Dict of metrics data
        """
        subject = f'[ALERT] Classification System Quality Issues - {timezone.now().strftime("%Y-%m-%d %H:%M")}'
        
        # Build message
        message_parts = [
            'Classification System Alert',
            '=' * 50,
            '',
            'The AI Message Classification System has detected quality issues:',
            '',
            'ISSUES:',
        ]
        
        for reason in reasons:
            message_parts.append(f'  ❌ {reason}')
        
        message_parts.extend([
            '',
            f'METRICS (Last {metrics["days"]} days):',
            f'  • Total Classifications: {metrics["total_count"]:,}',
            f'  • Average Confidence: {metrics["avg_confidence"]:.3f}',
            f'  • Low Confidence Rate: {metrics["low_confidence_rate"]*100:.1f}% ({metrics["low_confidence_count"]:,} classifications)',
            f'  • Slow Classification Rate: {metrics["slow_rate"]*100:.1f}% ({metrics["slow_count"]:,} classifications)',
            f'  • Average Processing Time: {metrics["avg_processing_time"]:.1f}ms',
            '',
        ])
        
        # Add low confidence examples
        if metrics.get('low_confidence_examples'):
            message_parts.append('LOW CONFIDENCE EXAMPLES:')
            for example in metrics['low_confidence_examples']:
                message_parts.append(
                    f'  • "{example["message"]}" -> {example["type"]} ({example["confidence"]:.2f})'
                )
            message_parts.append('')
        
        message_parts.extend([
            'RECOMMENDED ACTIONS:',
            f'  1. Review classification logs in Django admin',
            f'  2. Run: python manage.py classification_metrics --days={metrics["days"]}',
            f'  3. Check for patterns in low confidence messages',
            f'  4. Consider tuning keyword weights or thresholds',
            f'  5. Review recent code changes that may affect classification',
            '',
        ])
        
        # Add admin link if SITE_URL is configured
        site_url = getattr(settings, 'SITE_URL', None)
        if site_url:
            message_parts.append(f'View logs: {site_url}/admin/communications/classificationlog/')
            message_parts.append('')
        
        message_parts.extend([
            'This is an automated alert from the Classification Monitoring System.',
            f'Alert generated at: {timezone.now().strftime("%Y-%m-%d %H:%M:%S %Z")}',
        ])
        
        message = '\n'.join(message_parts)
        
        # Send email
        try:
            send_mail(
                subject,
                message,
                getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
                [email],
                fail_silently=False,
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Failed to send email alert: {str(e)}'))
            self.stderr.write('Please check your email configuration in Django settings.')
