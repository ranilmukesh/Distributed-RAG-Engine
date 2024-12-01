from typing import Dict, Any
import os
from dotenv import load_dotenv

def load_llm_config() -> Dict[str, Any]:
    """Load LLM configuration from environment variables"""
    load_dotenv()
    
    # Default to OpenAI if no provider specified
    provider = os.getenv("LLM_PROVIDER", "openai")
    
    config = {
        "openai": {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "model": os.getenv("OPENAI_MODEL", "gpt-4")
        },
        "anthropic": {
            "api_key": os.getenv("ANTHROPIC_API_KEY"),
            "model": os.getenv("ANTHROPIC_MODEL", "claude-2")
        },
        "cohere": {
            "api_key": os.getenv("COHERE_API_KEY"),
            "model": os.getenv("COHERE_MODEL", "command")
        },
        "azure": {
            "api_key": os.getenv("AZURE_OPENAI_API_KEY"),
            "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "api_version": os.getenv("AZURE_OPENAI_API_VERSION"),
            "deployment_name": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        },
        "nvidia": {
            "api_key": os.getenv("NVIDIA_API_KEY"),
            "model": os.getenv("NVIDIA_MODEL", "microsoft/phi-3-small-128k-instruct")
        }
    }
    
    return provider, config[provider]