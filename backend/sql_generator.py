"""
Converts natural-language user queries to SQL using the OpenAI Chat API.
"""
import os
import re

from openai import OpenAI
from dotenv import load_dotenv

from database import get_schema_description

load_dotenv()

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "OPENAI_API_KEY is not set. "
                "Copy backend/.env.example to backend/.env and add your key."
            )
        _client = OpenAI(api_key=api_key)
    return _client


_SYSTEM_PROMPT = """
You are an expert SQL assistant for a banking application.

{schema}

Rules you MUST follow:
1. Generate ONLY a single SELECT query – no INSERT, UPDATE, DELETE, DROP, or any DDL.
2. Do NOT include SQL comments (-- or /* */).
3. Do NOT use semicolons.
4. Always use table aliases for clarity.
5. Limit results to 100 rows unless the user specifies otherwise.
6. Use DATE('now') for today's date in SQLite.
7. Return ONLY the raw SQL query with no markdown fences, no explanation.
""".format(
    schema=get_schema_description()
)


_MAX_ROWS = 100


def _enforce_limit(sql: str, max_rows: int = _MAX_ROWS) -> str:
    """Append a LIMIT clause if none is already present."""
    if not re.search(r"\bLIMIT\b", sql, re.IGNORECASE):
        sql = f"{sql} LIMIT {max_rows}"
    return sql


def natural_language_to_sql(user_query: str) -> str:
    """
    Call OpenAI to translate *user_query* into a safe SELECT SQL statement.
    Returns the raw SQL string with a LIMIT enforced.
    """
    client = _get_client()
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        temperature=0,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_query},
        ],
    )
    sql = response.choices[0].message.content or ""
    # Strip any accidental markdown fences
    sql = re.sub(r"```(?:sql)?", "", sql, flags=re.IGNORECASE).strip().rstrip(";")
    return _enforce_limit(sql)
