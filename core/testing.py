"""
Testing utilities for behavioral equivalence testing and service layer validation.

This module provides base test classes and helper functions for testing
the refactored service layer and ensuring behavioral equivalence with
the original implementation.
"""
import json
from typing import Any, Dict, Optional
from django.test import TestCase, Client
from rest_framework.test import APITestCase, APIClient
from rest_framework import status


class BehavioralEquivalenceTestCase(APITestCase):
    """Base test case for behavioral equivalence testing.
    
    This test case provides utilities for comparing API responses before
    and after refactoring to ensure identical behavior.
    
    Usage:
        class TestTaskAPIEquivalence(BehavioralEquivalenceTestCase):
            def test_create_task_equivalence(self):
                # Make request to refactored endpoint
                response = self.client.post('/api/tasks/', data)
                
                # Verify response matches expected behavior
                self.assert_response_valid(response, status.HTTP_201_CREATED)
    """
    
    def setUp(self):
        """Set up test client and common test data."""
        super().setUp()
        self.client = APIClient()
        self.response_cache = {}
    
    def assert_response_valid(
        self,
        response,
        expected_status: int,
        expected_keys: Optional[list] = None
    ) -> None:
        """Assert that an API response is valid.
        
        Args:
            response: The API response object
            expected_status: Expected HTTP status code
            expected_keys: Optional list of keys that should be in response data
            
        Raises:
            AssertionError: If response is invalid
        """
        self.assertEqual(
            response.status_code,
            expected_status,
            f"Expected status {expected_status}, got {response.status_code}. "
            f"Response: {response.data if hasattr(response, 'data') else response.content}"
        )
        
        if expected_keys and hasattr(response, 'data'):
            response_data = response.data
            if isinstance(response_data, dict):
                for key in expected_keys:
                    self.assertIn(
                        key,
                        response_data,
                        f"Expected key '{key}' not found in response: {response_data}"
                    )
    
    def assert_response_no_error(self, response) -> None:
        """Assert that an API response contains no error.
        
        Args:
            response: The API response object
            
        Raises:
            AssertionError: If response contains an error
        """
        if hasattr(response, 'data') and isinstance(response.data, dict):
            self.assertNotIn(
                'error',
                response.data,
                f"Response contains error: {response.data}"
            )
            self.assertNotIn(
                'errors',
                response.data,
                f"Response contains errors: {response.data}"
            )
    
    def compare_responses(
        self,
        response1,
        response2,
        ignore_fields: Optional[list] = None
    ) -> bool:
        """Compare two API responses for equivalence.
        
        Args:
            response1: First API response
            response2: Second API response
            ignore_fields: Optional list of fields to ignore in comparison
            
        Returns:
            True if responses are equivalent, False otherwise
        """
        ignore_fields = ignore_fields or ['id', 'created_at', 'updated_at']
        
        # Compare status codes
        if response1.status_code != response2.status_code:
            return False
        
        # Compare response data
        if hasattr(response1, 'data') and hasattr(response2, 'data'):
            data1 = self._normalize_response_data(response1.data, ignore_fields)
            data2 = self._normalize_response_data(response2.data, ignore_fields)
            return data1 == data2
        
        return True
    
    def _normalize_response_data(
        self,
        data: Any,
        ignore_fields: list
    ) -> Any:
        """Normalize response data for comparison.
        
        Removes fields that should be ignored and converts to comparable format.
        
        Args:
            data: Response data to normalize
            ignore_fields: Fields to remove
            
        Returns:
            Normalized data
        """
        if isinstance(data, dict):
            return {
                k: self._normalize_response_data(v, ignore_fields)
                for k, v in data.items()
                if k not in ignore_fields
            }
        elif isinstance(data, list):
            return [self._normalize_response_data(item, ignore_fields) for item in data]
        else:
            return data
    
    def cache_response(self, key: str, response) -> None:
        """Cache an API response for later comparison.
        
        Args:
            key: Cache key
            response: Response to cache
        """
        self.response_cache[key] = {
            'status_code': response.status_code,
            'data': response.data if hasattr(response, 'data') else response.content,
        }
    
    def get_cached_response(self, key: str) -> Optional[Dict]:
        """Retrieve a cached API response.
        
        Args:
            key: Cache key
            
        Returns:
            Cached response or None if not found
        """
        return self.response_cache.get(key)


class ServiceLayerTestCase(TestCase):
    """Base test case for service layer testing.
    
    This test case provides utilities for testing service layer methods
    in isolation from HTTP concerns.
    
    Usage:
        class TestTaskService(ServiceLayerTestCase):
            def test_create_task_success(self):
                user = self.create_test_user()
                data = {'title': 'Test Task', 'priority': 'high'}
                
                task = TaskService.create_task(user, data)
                
                self.assertEqual(task.title, 'Test Task')
                self.assertEqual(task.created_by, user)
    """
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.test_data = {}
    
    def assert_exception_raised(
        self,
        exception_class,
        callable_func,
        *args,
        **kwargs
    ) -> None:
        """Assert that a specific exception is raised.
        
        Args:
            exception_class: Expected exception class
            callable_func: Function to call
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Raises:
            AssertionError: If exception is not raised
        """
        with self.assertRaises(exception_class):
            callable_func(*args, **kwargs)
    
    def assert_exception_message(
        self,
        exception_class,
        callable_func,
        expected_message: str,
        *args,
        **kwargs
    ) -> None:
        """Assert that a specific exception with message is raised.
        
        Args:
            exception_class: Expected exception class
            callable_func: Function to call
            expected_message: Expected message in exception
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Raises:
            AssertionError: If exception is not raised or message doesn't match
        """
        with self.assertRaises(exception_class) as context:
            callable_func(*args, **kwargs)
        
        self.assertIn(
            expected_message,
            str(context.exception),
            f"Expected message '{expected_message}' not found in exception: {context.exception}"
        )


class APIResponseComparator:
    """Utility class for comparing API responses.
    
    This class provides methods for comparing API responses from different
    implementations to verify behavioral equivalence.
    
    Usage:
        comparator = APIResponseComparator()
        response1 = client.get('/api/tasks/')
        response2 = client.get('/api/tasks/')
        
        is_equivalent = comparator.compare(response1, response2)
    """
    
    def __init__(self, ignore_fields: Optional[list] = None):
        """Initialize comparator.
        
        Args:
            ignore_fields: Fields to ignore in comparison (default: id, timestamps)
        """
        self.ignore_fields = ignore_fields or [
            'id', 'created_at', 'updated_at', 'created_on', 'modified_on'
        ]
    
    def compare(self, response1, response2) -> bool:
        """Compare two API responses.
        
        Args:
            response1: First response
            response2: Second response
            
        Returns:
            True if responses are equivalent
        """
        # Compare status codes
        if response1.status_code != response2.status_code:
            return False
        
        # Compare data
        if hasattr(response1, 'data') and hasattr(response2, 'data'):
            return self._compare_data(response1.data, response2.data)
        
        return True
    
    def _compare_data(self, data1: Any, data2: Any) -> bool:
        """Recursively compare response data.
        
        Args:
            data1: First data
            data2: Second data
            
        Returns:
            True if data is equivalent
        """
        if isinstance(data1, dict) and isinstance(data2, dict):
            # Compare keys (excluding ignored fields)
            keys1 = {k for k in data1.keys() if k not in self.ignore_fields}
            keys2 = {k for k in data2.keys() if k not in self.ignore_fields}
            
            if keys1 != keys2:
                return False
            
            # Compare values
            for key in keys1:
                if not self._compare_data(data1[key], data2[key]):
                    return False
            
            return True
        
        elif isinstance(data1, list) and isinstance(data2, list):
            if len(data1) != len(data2):
                return False
            
            return all(
                self._compare_data(item1, item2)
                for item1, item2 in zip(data1, data2)
            )
        
        else:
            return data1 == data2
    
    def get_differences(self, response1, response2) -> Dict[str, Any]:
        """Get differences between two responses.
        
        Args:
            response1: First response
            response2: Second response
            
        Returns:
            Dictionary describing differences
        """
        differences = {}
        
        if response1.status_code != response2.status_code:
            differences['status_code'] = {
                'response1': response1.status_code,
                'response2': response2.status_code,
            }
        
        if hasattr(response1, 'data') and hasattr(response2, 'data'):
            data_diff = self._get_data_differences(response1.data, response2.data)
            if data_diff:
                differences['data'] = data_diff
        
        return differences
    
    def _get_data_differences(self, data1: Any, data2: Any, path: str = '') -> Dict:
        """Recursively find differences in data.
        
        Args:
            data1: First data
            data2: Second data
            path: Current path in data structure
            
        Returns:
            Dictionary of differences
        """
        differences = {}
        
        if isinstance(data1, dict) and isinstance(data2, dict):
            all_keys = set(data1.keys()) | set(data2.keys())
            
            for key in all_keys:
                if key in self.ignore_fields:
                    continue
                
                new_path = f"{path}.{key}" if path else key
                
                if key not in data1:
                    differences[new_path] = {'missing_in': 'response1'}
                elif key not in data2:
                    differences[new_path] = {'missing_in': 'response2'}
                else:
                    sub_diff = self._get_data_differences(data1[key], data2[key], new_path)
                    differences.update(sub_diff)
        
        elif isinstance(data1, list) and isinstance(data2, list):
            if len(data1) != len(data2):
                differences[path] = {
                    'length_response1': len(data1),
                    'length_response2': len(data2),
                }
            else:
                for i, (item1, item2) in enumerate(zip(data1, data2)):
                    new_path = f"{path}[{i}]"
                    sub_diff = self._get_data_differences(item1, item2, new_path)
                    differences.update(sub_diff)
        
        elif data1 != data2:
            differences[path] = {
                'response1': data1,
                'response2': data2,
            }
        
        return differences
