# AI Message Classification System - Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the AI Message Classification System to production.

**System Performance:**
- Accuracy: 96.7%
- Performance: 15ms @ 95th percentile
- Low Confidence Rate: ~3%

---

## Pre-Deployment Checklist

### 1. Code Review

- [ ] All tests passing
- [ ] Code reviewed and approved
- [ ] No critical security issues
- [ ] Documentation updated
- [ ] Changelog updated

### 2. Testing

```bash
# Run all tests
python manage.py test communications.tests.test_classifier
python manage.py test communications.tests.test_integration
python manage.py test communications.tests.test_properties
python manage.py test communications.tests.test_performance_profiling

# Verify accuracy
python manage.py tune_thresholds --target-accuracy=0.90 --test-dataset
```

**Expected Results:**
- All tests pass
- Accuracy ≥90%
- 95th percentile <200ms

### 3. Configuration Review

- [ ] Thresholds configured appropriately
- [ ] Feature flag set (if using gradual rollout)
- [ ] Logging configured
- [ ] Email alerts configured
- [ ] Database settings verified

### 4. Database Preparation

```bash
# Check migrations
python manage.py makemigrations --check

# Test migration (dry run)
python manage.py migrate --plan

# Verify ClassificationLog model
python manage.py shell
>>> from communications.models import ClassificationLog
>>> ClassificationLog.objects.count()
```

### 5. Backup

```bash
# Backup database
python manage.py dumpdata communications > backup_communications_$(date +%Y%m%d).json

# Tag release
git tag -a v1.0-classification -m "Classification system deployment"
git push origin v1.0-classification

# Backup current code
tar -czf backup_code_$(date +%Y%m%d).tar.gz /path/to/project
```

---

## Deployment Steps

### Step 1: Maintenance Mode (Optional)

```bash
# Enable maintenance mode
touch /var/www/maintenance.flag

# Or update load balancer to show maintenance page
```

### Step 2: Pull Latest Code

```bash
# Navigate to project directory
cd /path/to/project

# Pull latest code
git fetch origin
git checkout main
git pull origin main

# Verify correct version
git log -1
```

### Step 3: Install Dependencies

```bash
# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# Verify scikit-learn installed
python -c "import sklearn; print(sklearn.__version__)"
```

### Step 4: Run Migrations

```bash
# Run migrations
python manage.py migrate

# Verify migration
python manage.py showmigrations communications
```

### Step 5: Load Keywords

```bash
# Load and verify keywords
python manage.py reload_keywords --verify --show-stats
```

**Expected Output:**
```
✓ Keywords reloaded successfully
  Old keyword count: 0
  New keyword count: 120+
  
✓ All keyword dictionaries valid

KEYWORD STATISTICS:
  Navigation: 20 keywords (avg weight: 0.75)
  Feature_Guide: 16 keywords (avg weight: 0.78)
  Company_Data: 25 keywords (avg weight: 0.82)
  Kenya_Governance: 30 keywords (avg weight: 0.85)
  Web_Search: 25 keywords (avg weight: 0.68)
  Tip: 15 keywords (avg weight: 0.75)
```


### Step 6: Collect Static Files

```bash
# Collect static files
python manage.py collectstatic --noinput

# Verify static files
ls -la /path/to/static/
```

### Step 7: Restart Services

```bash
# Restart Gunicorn
sudo systemctl restart gunicorn

# Verify service status
sudo systemctl status gunicorn

# Or if using Docker
docker-compose restart web

# Verify container status
docker-compose ps
```

### Step 8: Smoke Testing

```bash
# Test classification in shell
python manage.py shell
```

```python
from communications.classifier import get_classifier, ClassificationContext
from communications.classification_keywords import get_keyword_dictionaries

# Initialize classifier
classifier = get_classifier()
classifier.keyword_dictionaries = get_keyword_dictionaries()
classifier._initialized = True

# Test each classification type
test_cases = [
    ("How do I create a company?", "Navigation"),
    ("What does the compliance score do?", "Feature_Guide"),
    ("What is my company's deadline?", "Company_Data"),
    ("What are the CMA requirements?", "Kenya_Governance"),
    ("What is the weather in Nairobi?", "Web_Search"),
    ("I'm confused", "Tip"),
]

for message, expected_type in test_cases:
    result = classifier.classify(message)
    status = "✓" if result.type == expected_type else "✗"
    print(f"{status} {message[:40]:40} → {result.type:20} ({result.confidence:.2f})")
```

**Expected Output:**
```
✓ How do I create a company?              → Navigation          (0.95)
✓ What does the compliance score do?      → Feature_Guide       (0.92)
✓ What is my company's deadline?          → Company_Data        (0.98)
✓ What are the CMA requirements?          → Kenya_Governance    (0.96)
✓ What is the weather in Nairobi?         → Web_Search          (0.88)
✓ I'm confused                             → Tip                 (0.90)
```

### Step 9: Health Check

```bash
# Check application health
curl http://localhost:8000/health

# Test AI chat endpoint
curl -X POST http://localhost:8000/api/ai-chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I create a company?"}'
```

### Step 10: Enable Monitoring

```bash
# Set up cron job for daily accuracy checks
crontab -e

# Add monitoring job (runs daily at 9 AM)
0 9 * * * cd /path/to/project && /path/to/venv/bin/python manage.py check_classification_accuracy --threshold=0.85 --days=1 --email=admin@example.com
```

### Step 11: Disable Maintenance Mode

```bash
# Remove maintenance flag
rm /var/www/maintenance.flag

# Or update load balancer to enable traffic
```

---

## Post-Deployment Validation

### Immediate Checks (First Hour)

```bash
# Check error logs
tail -f /var/log/django/error.log

# Check classification logs
python manage.py shell
>>> from communications.models import ClassificationLog
>>> ClassificationLog.objects.filter(timestamp__gte=timezone.now() - timedelta(hours=1)).count()
>>> # Should see classifications being logged
```

### 24-Hour Monitoring

```bash
# Run metrics after 24 hours
python manage.py classification_metrics --days=1
```

**Expected Metrics:**
- Total Classifications: >100
- Average Confidence: >0.75
- High Confidence Rate: >80%
- Low Confidence Rate: <10%
- 95th Percentile Time: <200ms

### Review Low Confidence Classifications

```bash
# Check Django admin
# Navigate to: /admin/communications/classificationlog/
# Filter by: confidence_score < 0.6
# Review messages and identify patterns
```

### Performance Validation

```bash
# Check performance metrics
python manage.py classification_metrics --days=1

# Look for:
# - 95th percentile <200ms
# - No slow classifications (>500ms)
# - Average processing time <50ms
```


---

## Gradual Rollout (Optional)

If using feature flag for gradual rollout:

### Phase 1: 10% of Users (Days 1-3)

```python
# In Django settings or environment variable
CLASSIFICATION_ENABLED = True
CLASSIFICATION_ROLLOUT_PERCENTAGE = 10
```

**Monitoring:**
```bash
# Daily metrics
python manage.py classification_metrics --days=1

# Daily accuracy check
python manage.py check_classification_accuracy --threshold=0.85 --days=1
```

**Success Criteria:**
- Accuracy ≥90%
- No critical errors
- Performance <200ms @ 95th percentile
- No user complaints

### Phase 2: 50% of Users (Days 4-7)

```python
CLASSIFICATION_ROLLOUT_PERCENTAGE = 50
```

**Monitoring:**
- Same as Phase 1
- Compare metrics between 10% and 50% rollout
- Monitor for any degradation

**Success Criteria:**
- Metrics consistent with Phase 1
- No increase in error rate
- Performance stable

### Phase 3: 100% of Users (Day 8+)

```python
CLASSIFICATION_ROLLOUT_PERCENTAGE = 100
```

**Monitoring:**
- Continue daily monitoring for 1 week
- Weekly monitoring thereafter

**Success Criteria:**
- System stable at full rollout
- Accuracy maintained ≥90%
- Performance maintained <200ms

---

## Rollback Procedure

### When to Rollback

Rollback immediately if:
- Accuracy drops below 80%
- Error rate exceeds 5%
- Performance degrades (>500ms @ 95th percentile)
- Critical bugs affecting users
- High volume of user complaints

### Quick Rollback (Feature Flag)

**Fastest method - no code changes:**

```python
# In Django settings or environment variable
CLASSIFICATION_ENABLED = False
```

```bash
# Restart services
sudo systemctl restart gunicorn
```

**Verification:**
```bash
# Test that legacy system is working
python manage.py shell
>>> from communications.ai_chat import generate_contextual_response
>>> response = generate_contextual_response("How do I create a company?", "", None)
>>> print(response[:100])
```

### Full Rollback (Code Revert)

```bash
# Revert to previous version
git log --oneline -10  # Find commit before classification
git revert <commit-hash>
git push origin main

# Or reset to previous tag
git reset --hard v0.9-pre-classification
git push origin main --force

# Restart services
sudo systemctl restart gunicorn

# Verify rollback
curl http://localhost:8000/health
```

### Post-Rollback

1. **Notify stakeholders**
   - Inform team of rollback
   - Document reason
   - Estimate time to fix

2. **Analyze root cause**
   - Review error logs
   - Analyze classification logs
   - Identify what went wrong

3. **Plan remediation**
   - Fix identified issues
   - Add tests for the issue
   - Update deployment checklist

4. **Schedule redeployment**
   - After fixes are tested
   - With enhanced monitoring
   - Consider gradual rollout

---

## Troubleshooting Deployment Issues

### Issue: Migrations Fail

**Error:** `django.db.utils.OperationalError: no such table`

**Solution:**
```bash
# Check migration status
python manage.py showmigrations communications

# Run migrations
python manage.py migrate communications

# If still failing, check database connection
python manage.py dbshell
```

### Issue: Keywords Not Loading

**Error:** `Keyword dictionaries not loaded`

**Solution:**
```bash
# Verify file exists
ls -la communications/classification_keywords.py

# Check for syntax errors
python -m py_compile communications/classification_keywords.py

# Reload keywords
python manage.py reload_keywords --verify
```

### Issue: Import Errors

**Error:** `ModuleNotFoundError: No module named 'sklearn'`

**Solution:**
```bash
# Install scikit-learn
pip install scikit-learn

# Verify installation
python -c "import sklearn; print(sklearn.__version__)"

# Restart services
sudo systemctl restart gunicorn
```

### Issue: Performance Degradation

**Symptom:** Classification takes >500ms

**Solution:**
```bash
# Profile performance
python manage.py test communications.tests.test_performance_profiling

# Check database performance
python manage.py dbshell
# Run: EXPLAIN ANALYZE SELECT * FROM communications_classificationlog LIMIT 100;

# Optimize if needed:
# - Add database indexes
# - Reduce semantic samples
# - Optimize keyword matching
```

### Issue: High Error Rate

**Symptom:** Many classification errors in logs

**Solution:**
```bash
# Check error logs
tail -100 /var/log/django/error.log | grep "Classification"

# Check classification logs
python manage.py shell
>>> from communications.models import ClassificationLog
>>> errors = ClassificationLog.objects.filter(confidence_score=0.0)
>>> for log in errors[:10]:
...     print(f"{log.message[:50]} - {log.reasoning}")

# Fix identified issues and redeploy
```

---

## Success Criteria

Deployment is successful when:

- [ ] All tests pass
- [ ] Accuracy ≥90%
- [ ] 95th percentile performance <200ms
- [ ] Low confidence rate <10%
- [ ] No critical errors in logs
- [ ] Monitoring alerts configured
- [ ] Smoke tests pass
- [ ] 24-hour metrics look healthy
- [ ] No user complaints
- [ ] Rollback procedure tested and documented

---

## Post-Deployment Tasks

### Week 1

- [ ] Daily metrics review
- [ ] Daily accuracy checks
- [ ] Monitor error logs
- [ ] Review low confidence classifications
- [ ] Collect user feedback

### Week 2-4

- [ ] Weekly metrics review
- [ ] Tune thresholds if needed
- [ ] Add keywords based on patterns
- [ ] Optimize performance if needed
- [ ] Document lessons learned

### Ongoing

- [ ] Monthly metrics review
- [ ] Quarterly threshold tuning
- [ ] Regular keyword updates
- [ ] Performance optimization
- [ ] User feedback incorporation

---

## Support and Escalation

### Level 1: Self-Service
- Check [Documentation](CLASSIFICATION_SYSTEM_DOCUMENTATION.md)
- Review [Quick Reference](CLASSIFICATION_QUICK_REFERENCE.md)
- Run diagnostic commands

### Level 2: Team Support
- Contact development team
- Provide error logs and metrics
- Share classification examples

### Level 3: Emergency
- Critical system failure
- Accuracy <80%
- High error rate (>5%)
- **Action:** Immediate rollback + escalate to senior team

---

**Deployment Guide Version**: 1.0  
**Last Updated**: 2024  
**System Version**: AI Message Classification System v1.0
