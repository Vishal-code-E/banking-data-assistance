"""
Database schema loader utility.
Provides schema information to agents for SQL generation and validation.
"""

from typing import Dict, Any


# Banking database schema
BANKING_SCHEMA: Dict[str, Dict[str, Any]] = {
    "customers": {
        "columns": {
            "customer_id": "INTEGER PRIMARY KEY",
            "name": "VARCHAR(255)",
            "email": "VARCHAR(255)",
            "phone": "VARCHAR(20)",
            "account_type": "VARCHAR(50)",
            "created_at": "TIMESTAMP",
            "status": "VARCHAR(20)"
        },
        "description": "Customer information and account details"
    },
    "accounts": {
        "columns": {
            "account_id": "INTEGER PRIMARY KEY",
            "customer_id": "INTEGER FOREIGN KEY",
            "account_number": "VARCHAR(50)",
            "balance": "DECIMAL(15,2)",
            "account_type": "VARCHAR(50)",
            "created_at": "TIMESTAMP",
            "status": "VARCHAR(20)"
        },
        "description": "Bank account information"
    },
    "transactions": {
        "columns": {
            "transaction_id": "INTEGER PRIMARY KEY",
            "account_id": "INTEGER FOREIGN KEY",
            "transaction_type": "VARCHAR(50)",
            "amount": "DECIMAL(15,2)",
            "description": "TEXT",
            "transaction_date": "TIMESTAMP",
            "status": "VARCHAR(20)",
            "merchant": "VARCHAR(255)"
        },
        "description": "Transaction history for all accounts"
    }
}


def get_schema() -> Dict[str, Dict[str, Any]]:
    """
    Get the complete banking database schema.

    Returns:
        Dictionary containing schema information
    """
    return BANKING_SCHEMA


def get_schema_as_text() -> str:
    """
    Get schema as formatted text for LLM prompts.

    Returns:
        Formatted schema description
    """
    schema_text = "# Banking Database Schema\n\n"

    for table_name, table_info in BANKING_SCHEMA.items():
        schema_text += f"## Table: {table_name}\n"
        schema_text += f"Description: {table_info['description']}\n"
        schema_text += "Columns:\n"

        for col_name, col_type in table_info['columns'].items():
            schema_text += f"  - {col_name}: {col_type}\n"

        schema_text += "\n"

    return schema_text


def get_table_names() -> list:
    """
    Get list of all table names.

    Returns:
        List of table names
    """
    return list(BANKING_SCHEMA.keys())


def get_columns_for_table(table_name: str) -> list:
    """
    Get column names for a specific table.

    Args:
        table_name: Name of the table

    Returns:
        List of column names or empty list if table not found
    """
    if table_name in BANKING_SCHEMA:
        return list(BANKING_SCHEMA[table_name]['columns'].keys())
    return []
