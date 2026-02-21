"""
AI Engine Configuration
Handles LLM provider settings and API keys
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class AIConfig:
    """AI Engine configuration settings"""
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    
    # Anthropic Configuration
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    
    # LLM Provider Settings
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")  # openai or anthropic
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4-turbo-preview")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2000"))
    
    @classmethod
    def validate(cls):
        """Validate that required API keys are present"""
        if cls.LLM_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required when using OpenAI provider")
        elif cls.LLM_PROVIDER == "anthropic" and not cls.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is required when using Anthropic provider")
    
    @classmethod
    def get_llm_settings(cls):
        """Get current LLM settings"""
        return {
            "provider": cls.LLM_PROVIDER,
            "model": cls.LLM_MODEL,
            "temperature": cls.LLM_TEMPERATURE,
            "max_tokens": cls.LLM_MAX_TOKENS
        }


# Global config instance
config = AIConfig()
