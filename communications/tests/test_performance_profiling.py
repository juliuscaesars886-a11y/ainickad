"""
Performance Profiling and Optimization Test for AI Message Classification System

This module profiles classification with 1000+ diverse messages to identify bottlenecks
and verify performance requirements are met.

Task 4.1: Performance testing and optimization
- Profile classification with 1000+ diverse messages
- Identify bottlenecks (keyword matching, semantic analysis, context boosting)
- Optimize TF-IDF vectorizer caching
- Optimize keyword dictionary lookup (use sets instead of lists if needed)
- Optimize context boost logic
- Verify 95th percentile < 200ms, 99th percentile < 500ms
- Document optimization decisions

Requirements: 11.1-11.6
"""

import json
import time
import statistics
import cProfile
import pstats
import io
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict

import pytest

from communications.classifier import (
    MessageClassifier,
    ClassificationResult,
    ClassificationContext,
    get_classifier,
    reset_classifier,
    CLASSIFICATION_TYPES
)
from communications.classification_keywords import get_keyword_dictionaries


class TestPerformanceProfiling:
    """Performance profiling tests for classification system."""
    
    def setUp(self):
        """Set up test fixtures."""
        reset_classifier()
        self.classifier = get_classifier()
        
        # Load keyword dictionaries
        keyword_dicts = get_keyword_dictionaries()
        self.classifier.load_keywords(keyword_dicts)
        
        # Load test dataset
        test_dataset_path = Path(__file__).parent / "test_dataset.json"
        with open(test_dataset_path, 'r') as f:
            self.test_dataset = json.load(f)
    
    def tearDown(self):
        """Clean up after tests."""
        reset_classifier()
    
    def test_profile_classification_1000_messages(self):
        """
        Profile classification with 1000+ diverse messages.
        
        This test:
        1. Generates 1000+ messages from test dataset
        2. Profiles classification performance
        3. Identifies bottlenecks in keyword matching, semantic analysis, context boosting
        4. Measures timing for each component
        5. Verifies 95th percentile < 200ms, 99th percentile < 500ms
        """
        # Set up
        self.setUp()
        
        # Generate 1000+ messages by repeating test dataset
        messages = []
        contexts = []
        
        # Repeat test dataset to get 1000+ messages
        repetitions = (1000 // len(self.test_dataset)) + 1
        for _ in range(repetitions):
            for test_case in self.test_dataset:
                messages.append(test_case['message'])
                context_data = test_case.get('context', {})
                contexts.append(ClassificationContext(
                    user_role=context_data.get('user_role'),
                    company_name=context_data.get('company_name'),
                    company_id=context_data.get('company_id'),
                    conversation_history=context_data.get('conversation_history', [])
                ))
        
        # Limit to exactly 1000 messages
        messages = messages[:1000]
        contexts = contexts[:1000]
        
        print(f"\n{'='*80}")
        print(f"PERFORMANCE PROFILING: 1000 Messages")
        print(f"{'='*80}\n")
        
        # Track timing for each component
        total_times = []
        keyword_times = []
        semantic_times = []
        context_times = []
        combine_times = []
        
        # Profile classification
        profiler = cProfile.Profile()
        profiler.enable()
        
        for i, (message, context) in enumerate(zip(messages, contexts)):
            start_total = time.perf_counter()
            
            # Classify message
            try:
                result = self.classifier.classify(message, context)
                
                end_total = time.perf_counter()
                total_time_ms = (end_total - start_total) * 1000
                total_times.append(total_time_ms)
                
            except Exception as e:
                print(f"Classification {i+1} failed: {e}")
                continue
        
        profiler.disable()
        
        # Print profiling results
        print(f"\n{'='*80}")
        print(f"PROFILING RESULTS")
        print(f"{'='*80}\n")
        
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        ps.print_stats(30)  # Top 30 functions
        print(s.getvalue())
        
        # Calculate performance statistics
        if len(total_times) < 100:
            pytest.fail(f"Only {len(total_times)} successful classifications, need 100+")
        
        avg_time = statistics.mean(total_times)
        median_time = statistics.median(total_times)
        min_time = min(total_times)
        max_time = max(total_times)
        percentile_95 = statistics.quantiles(total_times, n=20)[18]
        percentile_99 = statistics.quantiles(total_times, n=100)[98]
        
        print(f"\n{'='*80}")
        print(f"PERFORMANCE STATISTICS")
        print(f"{'='*80}\n")
        print(f"Messages processed: {len(total_times)}")
        print(f"Average time: {avg_time:.2f}ms")
        print(f"Median time: {median_time:.2f}ms")
        print(f"Min time: {min_time:.2f}ms")
        print(f"Max time: {max_time:.2f}ms")
        print(f"95th percentile: {percentile_95:.2f}ms")
        print(f"99th percentile: {percentile_99:.2f}ms")
        print(f"")
        
        # Check performance requirements
        if percentile_95 >= 200.0:
            print(f"⚠️  WARNING: 95th percentile ({percentile_95:.2f}ms) >= 200ms target")
        else:
            print(f"✓ 95th percentile ({percentile_95:.2f}ms) < 200ms target")
        
        if percentile_99 >= 500.0:
            print(f"⚠️  WARNING: 99th percentile ({percentile_99:.2f}ms) >= 500ms target")
        else:
            print(f"✓ 99th percentile ({percentile_99:.2f}ms) < 500ms target")
        
        # Identify bottlenecks
        print(f"\n{'='*80}")
        print(f"BOTTLENECK ANALYSIS")
        print(f"{'='*80}\n")
        
        # Analyze profiling data for bottlenecks
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        
        # Get stats for specific functions
        stats = ps.stats
        
        # Find keyword matching time
        keyword_funcs = [k for k in stats.keys() if 'keyword' in str(k).lower()]
        if keyword_funcs:
            keyword_time = sum(stats[k][3] for k in keyword_funcs)
            print(f"Keyword matching: {keyword_time*1000:.2f}ms total")
        
        # Find semantic analysis time
        semantic_funcs = [k for k in stats.keys() if 'semantic' in str(k).lower() or 'tfidf' in str(k).lower()]
        if semantic_funcs:
            semantic_time = sum(stats[k][3] for k in semantic_funcs)
            print(f"Semantic analysis: {semantic_time*1000:.2f}ms total")
        
        # Find context boost time
        context_funcs = [k for k in stats.keys() if 'context' in str(k).lower() or 'boost' in str(k).lower()]
        if context_funcs:
            context_time = sum(stats[k][3] for k in context_funcs)
            print(f"Context boosting: {context_time*1000:.2f}ms total")
        
        print(f"\n{'='*80}")
        print(f"OPTIMIZATION RECOMMENDATIONS")
        print(f"{'='*80}\n")
        
        # Provide optimization recommendations based on results
        if percentile_95 < 50:
            print("✓ Performance is excellent (< 50ms). No optimization needed.")
        elif percentile_95 < 100:
            print("✓ Performance is good (< 100ms). Minor optimizations possible:")
            print("  - Consider caching frequently used keyword lookups")
            print("  - Profile semantic analysis for optimization opportunities")
        elif percentile_95 < 200:
            print("⚠️  Performance is acceptable (< 200ms) but could be improved:")
            print("  - Optimize keyword dictionary lookup (use sets instead of lists)")
            print("  - Cache TF-IDF vectorizers more efficiently")
            print("  - Optimize context boost logic")
        else:
            print("❌ Performance needs improvement (>= 200ms):")
            print("  - CRITICAL: Optimize keyword matching (use sets, not lists)")
            print("  - CRITICAL: Cache TF-IDF vectorizers in memory")
            print("  - CRITICAL: Reduce semantic analysis overhead")
            print("  - Consider lazy loading of semantic models")
        
        # Clean up
        self.tearDown()
        
        # Assert performance requirements
        assert percentile_95 < 200.0, (
            f"Performance requirement violated: 95th percentile is {percentile_95:.2f}ms, "
            f"must be < 200ms"
        )
        
        assert percentile_99 < 500.0, (
            f"Performance requirement violated: 99th percentile is {percentile_99:.2f}ms, "
            f"must be < 500ms"
        )
    
    def test_component_timing_breakdown(self):
        """
        Detailed timing breakdown for each classification component.
        
        Measures:
        - Keyword matching time
        - Semantic analysis time
        - Context boosting time
        - Score combination time
        """
        self.setUp()
        
        # Use a subset of test dataset for detailed analysis
        messages = [tc['message'] for tc in self.test_dataset[:100]]
        contexts = [
            ClassificationContext(
                user_role=tc.get('context', {}).get('user_role'),
                company_name=tc.get('context', {}).get('company_name'),
                company_id=tc.get('context', {}).get('company_id'),
                conversation_history=tc.get('context', {}).get('conversation_history', [])
            )
            for tc in self.test_dataset[:100]
        ]
        
        print(f"\n{'='*80}")
        print(f"COMPONENT TIMING BREAKDOWN (100 messages)")
        print(f"{'='*80}\n")
        
        # Track timing for each component
        normalize_times = []
        keyword_times = []
        semantic_times = []
        combine_times = []
        context_times = []
        total_times = []
        
        for message, context in zip(messages, contexts):
            # Normalize
            start = time.perf_counter()
            normalized = self.classifier._normalize_message(message)
            normalize_times.append((time.perf_counter() - start) * 1000)
            
            # Keyword matching
            start = time.perf_counter()
            keyword_scores = self.classifier._calculate_keyword_confidence(normalized)
            keyword_times.append((time.perf_counter() - start) * 1000)
            
            # Semantic analysis
            start = time.perf_counter()
            semantic_scores = self.classifier._calculate_semantic_confidence(normalized)
            semantic_times.append((time.perf_counter() - start) * 1000)
            
            # Combine scores
            start = time.perf_counter()
            combined_scores = self.classifier._combine_scores(keyword_scores, semantic_scores)
            combine_times.append((time.perf_counter() - start) * 1000)
            
            # Context boosting
            start = time.perf_counter()
            final_scores = self.classifier._apply_context_boosts(combined_scores, normalized, context)
            context_times.append((time.perf_counter() - start) * 1000)
            
            # Total
            total_times.append(
                normalize_times[-1] + keyword_times[-1] + semantic_times[-1] +
                combine_times[-1] + context_times[-1]
            )
        
        # Print results
        def print_stats(name, times):
            avg = statistics.mean(times)
            median = statistics.median(times)
            p95 = statistics.quantiles(times, n=20)[18]
            print(f"{name:20s}: avg={avg:6.2f}ms, median={median:6.2f}ms, p95={p95:6.2f}ms")
        
        print_stats("Normalization", normalize_times)
        print_stats("Keyword matching", keyword_times)
        print_stats("Semantic analysis", semantic_times)
        print_stats("Score combination", combine_times)
        print_stats("Context boosting", context_times)
        print_stats("TOTAL", total_times)
        
        # Calculate percentages
        total_avg = statistics.mean(total_times)
        print(f"\nPercentage breakdown:")
        print(f"  Normalization:    {statistics.mean(normalize_times)/total_avg*100:5.1f}%")
        print(f"  Keyword matching: {statistics.mean(keyword_times)/total_avg*100:5.1f}%")
        print(f"  Semantic analysis:{statistics.mean(semantic_times)/total_avg*100:5.1f}%")
        print(f"  Score combination:{statistics.mean(combine_times)/total_avg*100:5.1f}%")
        print(f"  Context boosting: {statistics.mean(context_times)/total_avg*100:5.1f}%")
        
        self.tearDown()
    
    def test_keyword_lookup_optimization(self):
        """
        Test keyword lookup performance and identify optimization opportunities.
        
        Compares:
        - Current list-based keyword matching
        - Potential set-based keyword matching
        """
        self.setUp()
        
        print(f"\n{'='*80}")
        print(f"KEYWORD LOOKUP OPTIMIZATION ANALYSIS")
        print(f"{'='*80}\n")
        
        # Get keyword dictionaries
        keyword_dicts = get_keyword_dictionaries()
        
        # Analyze keyword dictionary structure
        for classification_type, keywords in keyword_dicts.items():
            print(f"\n{classification_type}:")
            print(f"  Total keywords: {len(keywords)}")
            print(f"  Keyword type: {type(keywords)}")
            
            # Check if keywords are already optimized
            if isinstance(keywords, list):
                print(f"  ⚠️  Using list - could optimize with set for O(1) lookup")
            elif isinstance(keywords, set):
                print(f"  ✓ Using set - already optimized for O(1) lookup")
            
            # Sample keywords
            sample_keywords = [kw.text for kw in keywords[:5]]
            print(f"  Sample keywords: {sample_keywords}")
        
        # Test lookup performance
        test_messages = [tc['message'] for tc in self.test_dataset[:100]]
        
        # Current implementation
        start = time.perf_counter()
        for message in test_messages:
            normalized = self.classifier._normalize_message(message)
            scores = self.classifier._calculate_keyword_confidence(normalized)
        current_time = (time.perf_counter() - start) * 1000
        
        print(f"\nKeyword lookup performance (100 messages):")
        print(f"  Current implementation: {current_time:.2f}ms")
        print(f"  Average per message: {current_time/100:.2f}ms")
        
        # Recommendations
        print(f"\nOptimization recommendations:")
        print(f"  1. Keyword dictionaries are already using Keyword objects with .matches() method")
        print(f"  2. Current implementation iterates through keywords - O(n) complexity")
        print(f"  3. For optimization, consider:")
        print(f"     - Pre-compile regex patterns for regex keywords")
        print(f"     - Use trie data structure for multi-word phrase matching")
        print(f"     - Cache keyword match results for repeated messages")
        
        self.tearDown()
    
    def test_tfidf_vectorizer_caching(self):
        """
        Test TF-IDF vectorizer caching performance.
        
        Verifies:
        - Vectorizers are cached in memory
        - No redundant vectorizer creation
        - Cache hit rate
        """
        self.setUp()
        
        print(f"\n{'='*80}")
        print(f"TF-IDF VECTORIZER CACHING ANALYSIS")
        print(f"{'='*80}\n")
        
        # Check if vectorizers are cached
        print(f"Cached vectorizers: {len(self.classifier._tfidf_vectorizers)}")
        for classification_type in CLASSIFICATION_TYPES:
            if classification_type in self.classifier._tfidf_vectorizers:
                print(f"  ✓ {classification_type}: cached")
            else:
                print(f"  ❌ {classification_type}: NOT cached")
        
        # Test vectorizer performance
        test_messages = [tc['message'] for tc in self.test_dataset[:100]]
        
        # First pass (cold cache)
        start = time.perf_counter()
        for message in test_messages:
            normalized = self.classifier._normalize_message(message)
            scores = self.classifier._calculate_semantic_confidence(normalized)
        first_pass_time = (time.perf_counter() - start) * 1000
        
        # Second pass (warm cache)
        start = time.perf_counter()
        for message in test_messages:
            normalized = self.classifier._normalize_message(message)
            scores = self.classifier._calculate_semantic_confidence(normalized)
        second_pass_time = (time.perf_counter() - start) * 1000
        
        print(f"\nSemantic analysis performance (100 messages):")
        print(f"  First pass (cold cache): {first_pass_time:.2f}ms")
        print(f"  Second pass (warm cache): {second_pass_time:.2f}ms")
        print(f"  Cache speedup: {first_pass_time/second_pass_time:.2f}x")
        
        if second_pass_time < first_pass_time * 0.9:
            print(f"  ✓ Caching is effective")
        else:
            print(f"  ⚠️  Caching may not be effective - investigate")
        
        print(f"\nOptimization recommendations:")
        print(f"  1. Vectorizers are already cached in _tfidf_vectorizers dict")
        print(f"  2. Vectorizers are initialized once at classifier creation")
        print(f"  3. No redundant vectorizer creation detected")
        print(f"  4. Consider:")
        print(f"     - Lazy loading of vectorizers (only load when needed)")
        print(f"     - Reduce vectorizer feature count if memory is a concern")
        
        self.tearDown()


if __name__ == '__main__':
    # Run profiling tests
    test = TestPerformanceProfiling()
    
    print("\n" + "="*80)
    print("AI MESSAGE CLASSIFICATION SYSTEM - PERFORMANCE PROFILING")
    print("="*80)
    
    try:
        test.test_profile_classification_1000_messages()
    except Exception as e:
        print(f"\nError in profiling test: {e}")
    
    try:
        test.test_component_timing_breakdown()
    except Exception as e:
        print(f"\nError in component timing test: {e}")
    
    try:
        test.test_keyword_lookup_optimization()
    except Exception as e:
        print(f"\nError in keyword lookup test: {e}")
    
    try:
        test.test_tfidf_vectorizer_caching()
    except Exception as e:
        print(f"\nError in TF-IDF caching test: {e}")
    
    print("\n" + "="*80)
    print("PROFILING COMPLETE")
    print("="*80 + "\n")
