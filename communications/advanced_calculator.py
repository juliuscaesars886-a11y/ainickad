"""
Advanced calculator with safe evaluation, percentage handling, and natural language support.
Supports: arithmetic, percentages, functions (sqrt, abs, round, floor, ceil, log, sin, cos)
"""
import re
import ast
import operator
import math


# -------------------------
# SAFE OPERATORS
# -------------------------
operators = {
    ast.Add:  operator.add,
    ast.Sub:  operator.sub,
    ast.Mult: operator.mul,
    ast.Div:  operator.truediv,
    ast.Pow:  operator.pow,
    ast.USub: operator.neg,   # negative numbers: -5
}

SAFE_FUNCTIONS = {
    'sqrt':  math.sqrt,
    'abs':   abs,
    'round': round,
    'floor': math.floor,
    'ceil':  math.ceil,
    'log':   math.log10,
    'sin':   math.sin,
    'cos':   math.cos,
}


def evaluate(node):
    """Safely evaluate AST node."""
    # Support both old ast.Num and new ast.Constant
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    elif hasattr(ast, 'Num') and isinstance(node, ast.Num):
        return node.n
    elif isinstance(node, ast.BinOp):
        left  = evaluate(node.left)
        right = evaluate(node.right)
        if isinstance(node.op, ast.Div) and right == 0:
            raise ZeroDivisionError("Cannot divide by zero")
        return operators[type(node.op)](left, right)
    elif isinstance(node, ast.UnaryOp):
        return operators[type(node.op)](evaluate(node.operand))
    elif isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in SAFE_FUNCTIONS:
            args = [evaluate(a) for a in node.args]
            return SAFE_FUNCTIONS[node.func.id](*args)
        raise ValueError("Unsupported function")
    else:
        raise ValueError(f"Unsupported node type: {type(node)}")


def safe_eval(expr):
    """Safely evaluate mathematical expression."""
    expr = expr.strip()
    if not expr:
        raise ValueError("Empty expression")
    tree = ast.parse(expr, mode='eval')
    return evaluate(tree.body)


# -------------------------
# PERCENTAGE HANDLER
# -------------------------
def handle_percentages(text):
    """Handle percentage expressions in natural language."""
    # "20% of 50" or "20 percent of 50"
    text = re.sub(
        r"(\d+\.?\d*)\s*(%|percent)\s+of\s+(\d+\.?\d*)",
        lambda m: str((float(m.group(1)) / 100) * float(m.group(3))),
        text
    )
    
    # "50 + 10%" or "50 - 10%"
    text = re.sub(
        r"(\d+\.?\d*)\s*([+\-])\s*(\d+\.?\d*)%",
        lambda m: str(
            float(m.group(1)) + (float(m.group(1)) * float(m.group(3)) / 100)
            if m.group(2) == "+"
            else float(m.group(1)) - (float(m.group(1)) * float(m.group(3)) / 100)
        ),
        text
    )
    
    # "50% off 200" (discount)
    text = re.sub(
        r"(\d+\.?\d*)%\s+off\s+(\d+\.?\d*)",
        lambda m: str(float(m.group(2)) - (float(m.group(1)) / 100) * float(m.group(2))),
        text
    )
    
    return text


# -------------------------
# FORMAT RESULT
# -------------------------
def format_result(result):
    """Return clean number — no trailing zeros or unnecessary decimals."""
    if isinstance(result, float):
        if result == int(result):
            return str(int(result))
        # round to 4 decimal places, strip trailing zeros
        return f"{result:,.10f}".rstrip('0').rstrip('.')
    return f"{result:,}"


# -------------------------
# MAIN CALCULATOR
# -------------------------
def calculate(text):
    """Calculate mathematical expression from natural language."""
    original = text.strip()
    if not original:
        return "Please give me something to calculate."
    
    text = text.lower().strip()
    
    # Strip natural language prefixes
    prefixes = [
        "what is", "what's", "whats", "calculate", "compute",
        "solve", "find", "how much is", "tell me", "can you calculate",
        "work out", "evaluate",
    ]
    for prefix in sorted(prefixes, key=len, reverse=True):  # longest first
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            break
    
    # Word-to-symbol replacements (order matters — longer phrases first)
    replacements = [
        ("to the power of", "**"),
        ("multiplied by",   "*"),
        ("multiply by",     "*"),
        ("divided by",      "/"),
        ("divide by",       "/"),
        ("squared",         "**2"),
        ("cubed",           "**3"),
        ("times",           "*"),
        ("plus",            "+"),
        ("add",             "+"),
        ("minus",           "-"),
        ("subtract",        "-"),
        ("over",            "/"),
        ("percent",         "%"),
        ("^",               "**"),
    ]
    for word, symbol in replacements:
        text = text.replace(word, symbol)
    
    # Remove commas from numbers: 1,000 → 1000
    text = re.sub(r"(\d),(\d{3})", r"\1\2", text)
    
    # Handle percentage expressions before stripping %
    text = handle_percentages(text)
    
    # Strip leftover % signs
    text = text.replace("%", "")
    
    # Preserve known function names, remove everything else non-math
    def clean(t):
        # Replace known function names with placeholders, clean, restore
        saved = {}
        for i, fn in enumerate(SAFE_FUNCTIONS.keys()):
            placeholder = f"__FN{i}__"
            if fn in t:
                saved[placeholder] = fn
                t = t.replace(fn, placeholder)
        
        # Now strip non-math characters
        t = re.sub(r"[^\d\s\+\-\*\/\.\(\)__FN\d]", "", t)
        
        # Restore function names
        for placeholder, fn in saved.items():
            t = t.replace(placeholder, fn)
        
        return t.strip()
    
    text = clean(text)
    
    if not text:
        return f"I couldn't find a math expression in: '{original}'"
    
    try:
        result = safe_eval(text)
        formatted = format_result(result)
        return formatted
    except ZeroDivisionError:
        return "❌ Can't divide by zero!"
    except Exception:
        return (
            f"I couldn't calculate '{original}'. "
            "Try something like '15% of 300', '100 * 12', or 'sqrt(16)'."
        )


# -------------------------
# TESTS
# -------------------------
if __name__ == "__main__":
    tests = [
        # Original 4
        ("20 percent of 50",            "10"),
        ("50 + 10%",                    "55"),
        ("200 minus 25 percent of 200", "150"),
        ("15% of 300",                  "45"),
        # Arithmetic
        ("what is 5 + 3",               "8"),
        ("calculate 100 * 12",          "1200"),
        ("2 ^ 10",                      "1024"),
        ("2 squared",                   "4"),
        ("3 cubed",                     "27"),
        ("100 / 3",                     "33.333"),
        ("0.5 * 200",                   "100"),
        ("-5 + 10",                     "5"),
        # Number formatting
        ("1,000 + 500",                 "1500"),
        # Percentages
        ("50% off 200",                 "100"),
        # Functions
        ("sqrt(16)",                    "4"),
        ("abs(-42)",                    "42"),
        # Edge cases
        ("10 / 0",                      "divide by zero"),
        ("",                            "Please give me"),
        ("hello world",                 "couldn't"),
    ]
    
    print(f"{'Input':<40} {'Result':<20} Status")
    print("-" * 75)
    for expr, expected in tests:
        result = str(calculate(expr))
        status = "✅" if expected.lower() in result.lower() else "❌"
        print(f"{expr:<40} {result:<20} {status}")
