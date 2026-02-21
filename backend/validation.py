"""
SQL Validation Layer for Banking Data Assistant
Implements strict validation rules to ensure only safe SELECT queries are executed
"""

import re
import logging
from typing import Tuple, List
from enum import Enum

from backend.config import settings

logger = logging.getLogger(__name__)


# ============================================================
# VALIDATION RESULT
# ============================================================

class ValidationResult:
    """Container for validation results"""
    
    def __init__(self, is_valid: bool, error: str = None, cleaned_sql: str = None):
        self.is_valid = is_valid
        self.error = error
        self.cleaned_sql = cleaned_sql
    
    def __bool__(self):
        return self.is_valid
    
    def __repr__(self):
        if self.is_valid:
            return f"ValidationResult(valid=True)"
        return f"ValidationResult(valid=False, error='{self.error}')"


# ============================================================
# DANGEROUS KEYWORDS & PATTERNS
# ============================================================

# SQL keywords that modify data (must be blocked)
DANGEROUS_KEYWORDS = {
    'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
    'TRUNCATE', 'REPLACE', 'MERGE', 'GRANT', 'REVOKE',
    'EXEC', 'EXECUTE', 'CALL', 'PRAGMA'
}

# SQL injection patterns to detect
INJECTION_PATTERNS = [
    r";\s*DROP",                    # Drop table injection
    r";\s*DELETE",                  # Delete injection
    r";\s*UPDATE",                  # Update injection
    r";\s*INSERT",                  # Insert injection
    r"UNION\s+SELECT",              # Union-based injection
    r"--",                          # SQL comment
    r"/\*",                         # Multi-line comment start
    r"\*/",                         # Multi-line comment end
    r"xp_",                         # SQL Server extended procedures
    r"sp_",                         # SQL Server stored procedures
    r"0x[0-9a-fA-F]+",             # Hex injection attempts
]


# ============================================================
# VALIDATION FUNCTIONS
# ============================================================

def clean_sql(sql: str) -> str:
    """
    Clean and normalize SQL query
    - Strip whitespace
    - Normalize whitespace
    - Remove extra spaces
    """
    if not sql:
        return ""
    
    # Strip leading/trailing whitespace
    sql = sql.strip()
    
    # Normalize internal whitespace (replace multiple spaces with single space)
    sql = re.sub(r'\s+', ' ', sql)
    
    return sql


def check_for_comments(sql: str) -> ValidationResult:
    """
    Check for SQL comments which could be used for injection
    Blocks: -- and /* */
    """
    if '--' in sql:
        return ValidationResult(
            is_valid=False,
            error="SQL comments (--) are not allowed"
        )
    
    if '/*' in sql or '*/' in sql:
        return ValidationResult(
            is_valid=False,
            error="SQL multi-line comments (/* */) are not allowed"
        )
    
    return ValidationResult(is_valid=True)


def check_for_multiple_statements(sql: str) -> ValidationResult:
    """
    Check for multiple SQL statements (separated by semicolons)
    Only single SELECT statements are allowed
    """
    # Remove trailing semicolon if exists
    sql_stripped = sql.rstrip(';').strip()
    
    # Check if there are any remaining semicolons (indicates multiple statements)
    if ';' in sql_stripped:
        return ValidationResult(
            is_valid=False,
            error="Multiple SQL statements are not allowed"
        )
    
    return ValidationResult(is_valid=True)


def check_statement_type(sql: str) -> ValidationResult:
    """
    Verify that the SQL statement is a SELECT query
    Blocks all other statement types
    """
    sql_upper = sql.upper().strip()
    
    # Must start with SELECT
    if not sql_upper.startswith('SELECT'):
        return ValidationResult(
            is_valid=False,
            error="Only SELECT statements are allowed"
        )
    
    return ValidationResult(is_valid=True)


def check_for_dangerous_keywords(sql: str) -> ValidationResult:
    """
    Check for dangerous SQL keywords that modify data
    """
    sql_upper = sql.upper()
    
    for keyword in DANGEROUS_KEYWORDS:
        # Use word boundary to match whole words only
        pattern = r'\b' + keyword + r'\b'
        if re.search(pattern, sql_upper):
            return ValidationResult(
                is_valid=False,
                error=f"Dangerous keyword '{keyword}' is not allowed"
            )
    
    return ValidationResult(is_valid=True)


def check_for_injection_patterns(sql: str) -> ValidationResult:
    """
    Check for common SQL injection patterns
    """
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, sql, re.IGNORECASE):
            return ValidationResult(
                is_valid=False,
                error=f"Potential SQL injection pattern detected"
            )
    
    return ValidationResult(is_valid=True)


def extract_table_names(sql: str) -> List[str]:
    """
    Extract table names from SQL query
    Simple extraction using FROM and JOIN clauses
    """
    tables = []
    sql_upper = sql.upper()
    
    # Pattern to match table names after FROM
    from_pattern = r'\bFROM\s+(\w+)'
    from_matches = re.findall(from_pattern, sql_upper)
    tables.extend(from_matches)
    
    # Pattern to match table names after JOIN
    join_pattern = r'\bJOIN\s+(\w+)'
    join_matches = re.findall(join_pattern, sql_upper)
    tables.extend(join_matches)
    
    # Remove duplicates and convert to lowercase
    tables = list(set([t.lower() for t in tables]))
    
    return tables


def check_table_authorization(sql: str) -> ValidationResult:
    """
    Verify that all referenced tables are in the allowed list
    Prevents access to unauthorized tables
    """
    try:
        tables = extract_table_names(sql)
        
        if not tables:
            return ValidationResult(
                is_valid=False,
                error="No valid table found in query"
            )
        
        allowed_tables_lower = [t.lower() for t in settings.ALLOWED_TABLES]
        
        for table in tables:
            if table not in allowed_tables_lower:
                return ValidationResult(
                    is_valid=False,
                    error=f"Table '{table}' is not authorized. Allowed tables: {settings.ALLOWED_TABLES}"
                )
        
        return ValidationResult(is_valid=True)
        
    except Exception as e:
        logger.error(f"Table authorization check failed: {e}")
        return ValidationResult(
            is_valid=False,
            error="Failed to parse table names from query"
        )


def check_query_length(sql: str, max_length: int = 5000) -> ValidationResult:
    """
    Check if query length is within acceptable limits
    Prevents DOS attacks with extremely large queries
    """
    if len(sql) > max_length:
        return ValidationResult(
            is_valid=False,
            error=f"Query length exceeds maximum allowed length of {max_length} characters"
        )
    
    return ValidationResult(is_valid=True)


# ============================================================
# MAIN VALIDATION FUNCTION
# ============================================================

def validate_sql(sql: str) -> ValidationResult:
    """
    Main validation function that runs all validation checks
    Returns ValidationResult with is_valid, error, and cleaned_sql
    
    Validation order:
    1. Clean and normalize SQL
    2. Check query length
    3. Check for comments
    4. Check for multiple statements
    5. Check statement type (SELECT only)
    6. Check for dangerous keywords
    7. Check for injection patterns
    8. Check table authorization
    """
    
    # Step 1: Basic validation
    if not sql or not sql.strip():
        return ValidationResult(
            is_valid=False,
            error="SQL query cannot be empty"
        )
    
    # Step 2: Clean SQL
    cleaned_sql = clean_sql(sql)
    
    # Step 3: Check query length
    result = check_query_length(cleaned_sql)
    if not result:
        return result
    
    # Step 4: Check for comments
    result = check_for_comments(cleaned_sql)
    if not result:
        return result
    
    # Step 5: Check for multiple statements
    result = check_for_multiple_statements(cleaned_sql)
    if not result:
        return result
    
    # Step 6: Check statement type
    result = check_statement_type(cleaned_sql)
    if not result:
        return result
    
    # Step 7: Check for dangerous keywords
    result = check_for_dangerous_keywords(cleaned_sql)
    if not result:
        return result
    
    # Step 8: Check for injection patterns
    result = check_for_injection_patterns(cleaned_sql)
    if not result:
        return result
    
    # Step 9: Check table authorization
    result = check_table_authorization(cleaned_sql)
    if not result:
        return result
    
    # All validations passed
    logger.info(f"SQL validation passed for query: {cleaned_sql[:100]}...")
    return ValidationResult(
        is_valid=True,
        cleaned_sql=cleaned_sql
    )


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

def is_safe_query(sql: str) -> Tuple[bool, str]:
    """
    Convenience function that returns (is_valid, error_message)
    For backward compatibility and simpler usage
    """
    result = validate_sql(sql)
    return result.is_valid, result.error
