"""
SQL safety validator – ensures only read-only SELECT queries are executed.
"""
import re

# Statements that may mutate data or the schema
_WRITE_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|REPLACE|MERGE"
    r"|ATTACH|DETACH|PRAGMA|GRANT|REVOKE|EXEC|EXECUTE|CALL|LOAD|COPY)\b",
    re.IGNORECASE,
)

# Allow only a single statement (no semicolon-chained queries)
_MULTI_STATEMENT = re.compile(r";\s*\S")

# Comment injection patterns
_COMMENT_PATTERN = re.compile(r"(--|/\*|\*/|#)")


def validate_query(sql: str) -> tuple[bool, str]:
    """
    Return (is_safe, reason).
    A query is safe only if it is a single SELECT statement with no write
    keywords, no comment injections, and no semicolon-chained statements.
    """
    stripped = sql.strip()

    if not stripped.upper().startswith("SELECT"):
        return False, "Only SELECT statements are allowed."

    if _WRITE_KEYWORDS.search(stripped):
        return False, "Query contains forbidden write/DDL keywords."

    if _MULTI_STATEMENT.search(stripped):
        return False, "Multiple statements are not allowed."

    if _COMMENT_PATTERN.search(stripped):
        return False, "SQL comments are not allowed."

    return True, "OK"
