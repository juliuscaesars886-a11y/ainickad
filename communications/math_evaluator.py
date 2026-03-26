"""
Safe mathematical expression evaluator.

This module provides a secure way to evaluate mathematical expressions without
using eval() or exec(), preventing code injection attacks.

Supports:
- Operators: +, -, *, /, %, ** (with correct precedence)
- Parentheses for grouping
- Numeric literals (integers and decimals)

Rejects:
- Function calls
- Variable assignments
- String operations
- Dangerous patterns (eval, exec, import, __, lambda, def, class)
"""

import operator
import logging
from typing import List, Union, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MathToken:
    """Token in a mathematical expression."""
    type: str  # 'NUMBER', 'OPERATOR', 'LPAREN', 'RPAREN'
    value: Union[float, str]


class MathParser:
    """
    Parser for mathematical expressions.
    
    Implements recursive descent parsing with operator precedence:
    - Exponentiation (**): highest precedence
    - Multiplication, Division, Modulo (*, /, %): medium precedence
    - Addition, Subtraction (+, -): lowest precedence
    - Parentheses override precedence
    """
    
    OPERATORS = {
        '+': (operator.add, 1),
        '-': (operator.sub, 1),
        '*': (operator.mul, 2),
        '/': (operator.truediv, 2),
        '%': (operator.mod, 2),
        '**': (operator.pow, 3),
    }
    
    def __init__(self):
        self.tokens: List[MathToken] = []
        self.position: int = 0
    
    def tokenize(self, expression: str) -> List[MathToken]:
        """
        Tokenize mathematical expression.
        
        Args:
            expression: String containing mathematical expression
            
        Returns:
            List of MathToken objects
            
        Raises:
            ValueError: If expression contains invalid syntax
        """
        tokens = []
        i = 0
        expression = expression.replace(' ', '')
        
        if not expression:
            raise ValueError("Empty expression")
        
        while i < len(expression):
            # Check for numbers (including decimals)
            if expression[i].isdigit() or expression[i] == '.':
                num_str = ''
                has_decimal = False
                
                while i < len(expression) and (expression[i].isdigit() or expression[i] == '.'):
                    if expression[i] == '.':
                        if has_decimal:
                            raise ValueError(f"Invalid number: multiple decimal points")
                        has_decimal = True
                    num_str += expression[i]
                    i += 1
                
                # Validate number format
                if num_str == '.':
                    raise ValueError(f"Invalid number: {num_str}")
                
                try:
                    tokens.append(MathToken('NUMBER', float(num_str)))
                except ValueError:
                    raise ValueError(f"Invalid number: {num_str}")
                continue
            
            # Check for ** operator (must check before single *)
            if expression[i:i+2] == '**':
                tokens.append(MathToken('OPERATOR', '**'))
                i += 2
                continue
            
            # Check for single-character operators
            if expression[i] in '+-*/%':
                tokens.append(MathToken('OPERATOR', expression[i]))
                i += 1
                continue
            
            # Check for parentheses
            if expression[i] == '(':
                tokens.append(MathToken('LPAREN', '('))
                i += 1
                continue
            
            if expression[i] == ')':
                tokens.append(MathToken('RPAREN', ')'))
                i += 1
                continue
            
            # Invalid character
            raise ValueError(f"Invalid character: {expression[i]}")
        
        return tokens
    
    def parse(self, expression: str) -> float:
        """
        Parse and evaluate mathematical expression.
        
        Args:
            expression: String containing mathematical expression
            
        Returns:
            Evaluated result as float
            
        Raises:
            ValueError: If expression is invalid or contains dangerous patterns
        """
        # Validate expression doesn't contain dangerous patterns
        expression_lower = expression.lower()
        dangerous_patterns = ['import', 'exec', 'eval', '__', 'lambda', 'def', 'class']
        
        for pattern in dangerous_patterns:
            if pattern in expression_lower:
                raise ValueError(f"Expression contains disallowed operations")
        
        # Tokenize
        self.tokens = self.tokenize(expression)
        self.position = 0
        
        # Parse and evaluate
        result = self._parse_expression()
        
        # Ensure all tokens consumed
        if self.position < len(self.tokens):
            raise ValueError("Unexpected tokens after expression")
        
        return result
    
    def _parse_expression(self) -> float:
        """Parse expression with operator precedence."""
        return self._parse_addition()
    
    def _parse_addition(self) -> float:
        """Parse addition and subtraction (lowest precedence)."""
        left = self._parse_multiplication()
        
        while self.position < len(self.tokens):
            token = self.tokens[self.position]
            if token.type == 'OPERATOR' and token.value in ['+', '-']:
                self.position += 1
                right = self._parse_multiplication()
                op_func, _ = self.OPERATORS[token.value]
                left = op_func(left, right)
            else:
                break
        
        return left
    
    def _parse_multiplication(self) -> float:
        """Parse multiplication, division, modulo (medium precedence)."""
        left = self._parse_exponentiation()
        
        while self.position < len(self.tokens):
            token = self.tokens[self.position]
            if token.type == 'OPERATOR' and token.value in ['*', '/', '%']:
                self.position += 1
                right = self._parse_exponentiation()
                op_func, _ = self.OPERATORS[token.value]
                
                # Check for division by zero
                if token.value == '/' and right == 0:
                    raise ValueError("Division by zero")
                
                left = op_func(left, right)
            else:
                break
        
        return left
    
    def _parse_exponentiation(self) -> float:
        """Parse exponentiation (highest precedence)."""
        left = self._parse_primary()
        
        while self.position < len(self.tokens):
            token = self.tokens[self.position]
            if token.type == 'OPERATOR' and token.value == '**':
                self.position += 1
                right = self._parse_primary()
                op_func, _ = self.OPERATORS[token.value]
                left = op_func(left, right)
            else:
                break
        
        return left
    
    def _parse_primary(self) -> float:
        """Parse primary expressions (numbers and parentheses)."""
        if self.position >= len(self.tokens):
            raise ValueError("Unexpected end of expression")
        
        token = self.tokens[self.position]
        
        # Number
        if token.type == 'NUMBER':
            self.position += 1
            return token.value
        
        # Parenthesized expression
        if token.type == 'LPAREN':
            self.position += 1
            result = self._parse_expression()
            
            if self.position >= len(self.tokens) or self.tokens[self.position].type != 'RPAREN':
                raise ValueError("Missing closing parenthesis")
            
            self.position += 1
            return result
        
        raise ValueError(f"Unexpected token: {token.type}")


class MathPrettyPrinter:
    """Pretty printer for mathematical expressions."""
    
    @staticmethod
    def format(expression: str) -> str:
        """
        Format mathematical expression with proper spacing.
        
        Args:
            expression: String containing mathematical expression
            
        Returns:
            Formatted expression with spaces around operators
        """
        # Remove existing spaces
        formatted = expression.replace(' ', '')
        
        # Use a placeholder for ** to avoid splitting it
        POWER_PLACEHOLDER = '\x00POWER\x00'
        formatted = formatted.replace('**', POWER_PLACEHOLDER)
        
        # Add spaces around single-character operators
        formatted = formatted.replace('+', ' + ')
        formatted = formatted.replace('-', ' - ')
        formatted = formatted.replace('*', ' * ')
        formatted = formatted.replace('/', ' / ')
        formatted = formatted.replace('%', ' % ')
        
        # Restore ** with proper spacing
        formatted = formatted.replace(POWER_PLACEHOLDER, ' ** ')
        
        # Clean up multiple spaces and spaces around parentheses
        formatted = ' '.join(formatted.split())
        formatted = formatted.replace('( ', '(')
        formatted = formatted.replace(' )', ')')
        
        return formatted


def evaluate_math_expression(expression: str) -> Optional[str]:
    """
    Safely evaluate a mathematical expression.
    
    This is a wrapper function that provides safe evaluation with error handling
    and result formatting. Supports both traditional math expressions and natural
    language math (e.g., "20% of 50", "sqrt(16)", "100 * 12").
    
    Args:
        expression: String containing mathematical expression
        
    Returns:
        Formatted result string, or None if evaluation fails
        
    Examples:
        >>> evaluate_math_expression("2 + 2")
        "4"
        >>> evaluate_math_expression("10 / 3")
        "3.333333"
        >>> evaluate_math_expression("5 * 6")
        "30"
        >>> evaluate_math_expression("20% of 50")
        "10"
        >>> evaluate_math_expression("sqrt(16)")
        "4"
        >>> evaluate_math_expression("invalid")
        None
    """
    try:
        # Try advanced calculator first (supports natural language and percentages)
        try:
            from communications.advanced_calculator import calculate
            result_str = calculate(expression)
            # Check if it's an error message
            if not any(err in result_str for err in ["couldn't", "divide by zero", "Please give me"]):
                return result_str
        except Exception:
            pass
        
        # Fallback to traditional parser
        parser = MathParser()
        result = parser.parse(expression)
        
        # Format result
        # If result is effectively an integer, display without decimals
        if result == int(result):
            return str(int(result))
        else:
            # Format with up to 6 decimals, removing trailing zeros
            formatted = f"{result:.6f}".rstrip('0').rstrip('.')
            return formatted
    
    except Exception as e:
        logger.warning(f"Math evaluation error for '{expression}': {e}")
        return None
