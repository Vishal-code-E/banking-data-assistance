"""
Structured logging utility for the AI Banking Assistant.
Provides consistent logging across all agents.
"""

import logging
import json
from datetime import datetime
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
            "timestamp": datetime.utcnow().isoformat(),
            "query": query
        }))
    
    def log_agent_execution(self, agent_name: str, input_data: Dict[str, Any], output_data: Dict[str, Any]) -> None:
        """Log agent execution details."""
        self.logger.info(json.dumps({
            "event": "agent_execution",
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent_name,
            "input": input_data,
            "output": output_data
        }))
    
    def log_sql_generation(self, sql: str, retry_count: int) -> None:
        """Log SQL generation."""
        self.logger.info(json.dumps({
            "event": "sql_generation",
            "timestamp": datetime.utcnow().isoformat(),
            "sql": sql,
            "retry_count": retry_count
        }))
    
    def log_validation_result(self, is_valid: bool, reason: str = None) -> None:
        """Log validation results."""
        self.logger.info(json.dumps({
            "event": "validation_result",
            "timestamp": datetime.utcnow().isoformat(),
            "is_valid": is_valid,
            "reason": reason
        }))
    
    def log_retry(self, retry_count: int, error: str) -> None:
        """Log retry attempts."""
        self.logger.warning(json.dumps({
            "event": "retry",
            "timestamp": datetime.utcnow().isoformat(),
            "retry_count": retry_count,
            "error": error
        }))
    
    def log_final_status(self, success: bool, validated_sql: str = None, error: str = None) -> None:
        """Log final workflow status."""
        self.logger.info(json.dumps({
            "event": "final_status",
            "timestamp": datetime.utcnow().isoformat(),
            "success": success,
            "validated_sql": validated_sql,
            "error": error
        }))

    def log_execution_time(self, agent_name: str, execution_time_seconds: float) -> None:
        """Log execution time for performance monitoring."""
        self.logger.info(json.dumps({
            "event": "execution_time",
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent_name,
            "execution_time_seconds": execution_time_seconds
        }))

    def log_error(self, error_message: str, context: Dict[str, Any] = None, error_type: str = "system") -> None:
        """Log errors with context and type classification.

        Args:
            error_message: The error message
            context: Additional context dict
            error_type: One of 'validation', 'execution', 'system', 'timeout'
        """
        self.logger.error(json.dumps({
            "event": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": error_message,
            "error_type": error_type,
            "context": context or {}
        }))


# Singleton instance
logger = StructuredLogger()
