"""
Structured logging utility for the AI Banking Assistant.
Provides consistent logging across all agents.
"""

import logging
import json
from datetime import datetime, timezone
from typing import Any, Dict


# Configure structured logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class StructuredLogger:
    """Structured logger for banking assistant operations."""

    def __init__(self, name: str = "BankingAssistant"):
        self.logger = logging.getLogger(name)

    def log_user_query(self, query: str) -> None:
        """Log incoming user query."""
        self.logger.info(json.dumps({
            "event": "user_query",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query": query
        }))

    def log_agent_execution(self, agent_name: str, input_data: Dict[str, Any], output_data: Dict[str, Any]) -> None:
        """Log agent execution details."""
        self.logger.info(json.dumps({
            "event": "agent_execution",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent_name,
            "input": input_data,
            "output": output_data
        }))

    def log_sql_generation(self, sql: str, retry_count: int) -> None:
        """Log SQL generation."""
        self.logger.info(json.dumps({
            "event": "sql_generation",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sql": sql,
            "retry_count": retry_count
        }))

    def log_validation_result(self, is_valid: bool, reason: str = None) -> None:
        """Log validation results."""
        self.logger.info(json.dumps({
            "event": "validation_result",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "is_valid": is_valid,
            "reason": reason
        }))

    def log_retry(self, retry_count: int, error: str) -> None:
        """Log retry attempts."""
        self.logger.warning(json.dumps({
            "event": "retry",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "retry_count": retry_count,
            "error": error
        }))

    def log_final_status(self, success: bool, validated_sql: str = None, error: str = None) -> None:
        """Log final workflow status."""
        self.logger.info(json.dumps({
            "event": "final_status",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "success": success,
            "validated_sql": validated_sql,
            "error": error
        }))

    def log_error(self, error_message: str, context: Dict[str, Any] = None) -> None:
        """Log errors with context."""
        self.logger.error(json.dumps({
            "event": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": error_message,
            "context": context or {}
        }))


# Singleton instance
logger = StructuredLogger()
