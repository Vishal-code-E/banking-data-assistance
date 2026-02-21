"""
Database schema loader utility.
Provides schema information to agents for SQL generation and validation.
"""

from typing import Dict, Any


# Banking database schema - matches actual schema.sql
# This is the exact schema used in the database
BANKING_SCHEMA: Dict[str, Dict[str, Any]] = {
    "customers": {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "name": "TEXT NOT NULL",
            "email": "TEXT NOT NULL UNIQUE",
            "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP"
        },
        "description": "Customer information"
    },
    "accounts": {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "customer_id": "INTEGER NOT NULL FOREIGN KEY -> customers(id)",
            "account_number": "TEXT NOT NULL UNIQUE",
            "balance": "DECIMAL(15,2) NOT NULL DEFAULT 0.00",
            "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP"
        },
        "description": "Customer bank accounts"
    },
    "transactions": {
        "columns": {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "account_id": "INTEGER NOT NULL FOREIGN KEY -> accounts(id)",
            "type": "TEXT NOT NULL CHECK(type IN ('credit', 'debit'))",
            "amount": "DECIMAL(15,2) NOT NULL",
            "created_at": "DATETIME DEFAULT CURRENT_TIMESTAMP"
        },
        "description": "All account transactions (credit or debit)"
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
