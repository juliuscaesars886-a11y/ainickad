#!/usr/bin/env python3
"""
Generate test dataset with 100+ labeled messages for classification accuracy testing.

This script creates a comprehensive test dataset covering all 6 classification types
with various edge cases, ambiguous messages, and context scenarios.
"""

import json

# Test dataset with 100+ labeled messages
test_dataset = [
    # Navigation queries (15 messages)
    {"message": "How do I create a new company?", "expected_type": "Navigation", "context": {}, "description": "Basic navigation query - company creation"},
    {"message": "Where is the staff management section?", "expected_type": "Navigation", "context": {}, "description": "Navigation query - finding staff section"},
    {"message": "How to upload documents to the system?", "expected_type": "Navigation", "context": {}, "description": "Navigation query - document upload"},
    {"message": "Where can I find the dashboard?", "expected_type": "Navigation", "context": {}, "description": "Navigation query - dashboard location"},
    {"message": "How do I access my company profile?", "expected_type": "Navigation", "context": {}, "description": "Navigation query - company profile access"},
    {"message": "Where is the compliance section?", "expected_type": "Navigation", "context": {}, "description": "Navigation query - compliance section"},
    {"message": "How to find the reporting feature?", "expected_type": "Navigation", "context": {}, "description": "Navigation query - reporting feature"},
    {"message": "Where can I view pending actions?", "expected_type": "Navigation", "context": {}, "description": "Navigation query - pending actions"},
    {"message": "How do I navigate to the settings menu?", "expected_type": "Navigation", "context": {}, "description": "Navigation query - settings menu"},
    {"message": "Where is the user management page?", "expected_type": "Navigation", "context": {}, "description": "Navigation query - user management"},
    {"message": "How to locate the document upload area?", "expected_type": "Navigation", "context": {}, "description": "Navigation query - document upload area"},
    {"message": "Where can I see the board meeting section?", "expected_type": "Navigation", "context": {}, "description": "Navigation query - board meeting section"},
    {"message": "How do I access the annual return filing page?", "expected_type": "Navigation", "context": {}, "description": "Navigation query - annual return filing"},
    {"message": "Where is the compliance checklist?", "expected_type": "Navigation", "context": {}, "description": "Navigation query - compliance checklist"},
    {"message": "How to find the notification settings?", "expected_type": "Navigation", "context": {}, "description": "Navigation query - notification settings"},
    
    # Feature Guide queries (15 messages)
    {"message": "What does the compliance score feature do?", "expected_type": "Feature_Guide", "context": {}, "description": "Feature guide query - compliance score explanation"},
    {"message": "How does the document management system work?", "expected_type": "Feature_Guide", "context": {}, "description": "Feature guide query - document management explanation"},
    {"message": "What is the purpose of the health score?", "expected_type": "Feature_Guide", "context": {}, "description": "Feature guide query - health score purpose"},
    {"message": "How does the annual return filing process work?", "expected_type": "Feature_Guide", "context": {}, "description": "Feature guide query - annual return process"},
    {"message": "What are the features of the board meeting module?", "expected_type": "Feature_Guide", "context": {}, "description": "Feature guide query - board meeting features"},
    {"message": "How does the user role system work?", "expected_type": "Feature_Guide", "context": {}, "description": "Feature guide query - user role system"},
    {"message": "What is the purpose of pending actions?", "expected_type": "Feature_Guide", "context": {}, "description": "Feature guide query - pending actions purpose"},
    {"message": "How does the notification system function?", "expected_type": "Feature_Guide", "context": {}, "description": "Feature guide query - notification system"},
    {"message": "What are the capabilities of the reporting tool?", "expected_type": "Feature_Guide", "context": {}, "description": "Feature guide query - reporting tool capabilities"},
    {"message": "How does the document versioning work?", "expected_type": "Feature_Guide", "context": {}, "description": "Feature guide query - document versioning"},
    {"message": "What is the purpose of the compliance checklist?", "expected_type": "Feature_Guide", "context": {}, "description": "Feature guide query - compliance checklist purpose"},
    {"messag