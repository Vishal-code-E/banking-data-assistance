"""
SQL security validation utilities.
Defense-in-depth approach with rule-based validation before LLM validation.
"""

import re
from typing import Tuple, List


# Maximum rows allowed in query results
MAX_ROW_LIMIT = 1000

# Default LIMIT to append if none specified
DEFAULT_LIMIT = 100

# Forbidden SQL keywords that indicate unsafe operations
FORBIDDEN_KEYWORDS = [
    "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE",
    "TRUNCATE", "REPLACE", "MERGE", "GRANT", "REVOKE",
    "EXEC", "EXECUTE", "CALL", "PROCEDURE", "FUNCTION"
]


def remove_sql_comments(sql: str) -> str:
    """
    Remove SQL comments from query.

    Args:
        sql: SQL query string

    Returns:
        SQL with comments removed
    """
    # Remove single-line comments
    sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)

    # Remove multi-line comments
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)

    return sql


def is_select_only(sql: str) -> bool:
    """
    Check if SQL query is SELECT-only.

    Args:
        sql: SQL query string

    Returns:
        True if query is SELECT-only, False otherwise
    """
    # Remove comments and normalize whitespace
    sql_clean = remove_sql_comments(sql).strip()

    # Empty query is invalid
    if not sql_clean:
        return False

    # Must start with SELECT (case-insensitive)
    return sql_clean.upper().startswith("SELECT")


def contains_forbidden_keywords(sql: str) -> Tuple[bool, List[str]]:
    """
    Check if SQL contains forbidden keywords.

    Args:
        sql: SQL query string

    Returns:
        Tuple of (has_forbidden, list_of_found_keywords)
    """
    sql_upper = remove_sql_comments(sql).upper()
    found_keywords = []

    for keyword in FORBIDDEN_KEYWORDS:
        # Use word boundaries to avoid false positives
        pattern = r'\b' + keyword + r'\b'
        if re.search(pattern, sql_upper):
            found_keywords.append(keyword)

    return (len(found_keywords) > 0, found_keywords)


def contains_multiple_statements(sql: str) -> bool:
    """
    Block multiple SQL statements separated by semicolons.

    Args:
        sql: SQL query string

    Returns:
        True if multiple statements detected
    """
    sql_clean = remove_sql_comments(sql).strip().rstrip(';')
    # If there's still a semicolon after stripping trailing one, it's multi-statement
    return ';' in sql_clean


def contains_union(sql: str) -> bool:
    """
    Block UNION-based injection attacks.

    Args:
        sql: SQL query string

    Returns:
        True if UNION keyword found
    """
    sql_clean = remove_sql_comments(sql).upper()
    return bool(re.search(r'\bUNION\b', sql_clean))


def enforce_limit(sql: str) -> str:
    """
    Ensure query has a LIMIT clause. Append default if missing.
    Cap existing LIMIT at MAX_ROW_LIMIT.

    Args:
        sql: SQL query string

    Returns:
        SQL with LIMIT enforced
    """
    sql_clean = sql.strip()
    sql_upper = sql_clean.upper()

    # Check if LIMIT already exists
    limit_match = re.search(r'\bLIMIT\s+(\d+)', sql_upper)
    if limit_match:
        existing_limit = int(limit_match.group(1))
        if existing_limit > MAX_ROW_LIMIT:
            # Cap at MAX_ROW_LIMIT
            sql_clean = re.sub(
                r'\bLIMIT\s+\d+',
                f'LIMIT {MAX_ROW_LIMIT}',
                sql_clean,
                flags=re.IGNORECASE
            )
        return sql_clean
    else:
        # Append default LIMIT
        return f"{sql_clean} LIMIT {DEFAULT_LIMIT}"


def validate_schema_tables(sql: str, schema: dict) -> Tuple[bool, str]:
    """
    Validate that all tables mentioned in SQL exist in schema.

    Args:
        sql: SQL query string
        schema: Database schema dict with table names as keys

    Returns:
        Tuple of (is_valid, error_message)
    """
    sql_clean = remove_sql_comments(sql)
    # Extract table names from SQL
    table_pattern = r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
    join_pattern = r'\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)'

    tables_in_query = set()

    for match in re.finditer(table_pattern, sql_clean, re.IGNORECASE):
        tables_in_query.add(match.group(1).lower())

    for match in re.finditer(join_pattern, sql_clean, re.IGNORECASE):
        tables_in_query.add(match.group(1).lower())

    # Check if all tables exist in schema
    available_tables = {table.lower() for table in schema.keys()}
    invalid_tables = tables_in_query - available_tables

    if invalid_tables:
        return False, f"Tables not found in schema: {', '.join(invalid_tables)}"

    return True, ""


def validate_sql_safety(sql: str, schema: dict) -> Tuple[bool, str]:
    """
    Comprehensive SQL safety validation.
    Combines all security checks.

    Args:
        sql: SQL query string
        schema: Database schema dict

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check 1: Must be SELECT only
    if not is_select_only(sql):
        return False, "Only SELECT queries are allowed"

    # Check 2: No multiple statements (prevents injection via stacked queries)
    if contains_multiple_statements(sql):
        return False, "Multiple SQL statements are not allowed"

    # Check 3: No UNION (prevents UNION-based injection)
    if contains_union(sql):
        return False, "UNION queries are not allowed"

    # Check 4: No forbidden keywords
    has_forbidden, forbidden_list = contains_forbidden_keywords(sql)
    if has_forbidden:
        return False, f"Forbidden keywords detected: {', '.join(forbidden_list)}"

    # Check 5: Validate schema tables
    tables_valid, table_error = validate_schema_tables(sql, schema)
    if not tables_valid:
        return False, table_error

    return True, "VALID"
