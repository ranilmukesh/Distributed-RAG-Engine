from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
import os
from llama_index.llms.openai import OpenAI
from llama_index.llms.anthropic import Anthropic
from llama_index.llms.cohere import Cohere
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.llms.nvidia import NVIDIA

class BaseLLMService(ABC):
    """Abstract base class for LLM services"""
    
    @abstractmethod
    def get_llm(self):
        """Get LLM instance"""
        pass

class OpenAIService(BaseLLMService):
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.api_key = api_key
        self.model = model

    def get_llm(self):
        return OpenAI(
            api_key=self.api_key,
            model=self.model,
            temperature=0.7
        )

class AnthropicService(BaseLLMService):
    def __init__(self, api_key: str, model: str = "claude-2"):
        self.api_key = api_key
        self.model = model

    def get_llm(self):
        return Anthropic(
            api_key=self.api_key,
            model=self.model
        )

class CohereService(BaseLLMService):
    def __init__(self, api_key: str, model: str = "command"):
        self.api_key = api_key
        self.model = model

    def get_llm(self):
        return Cohere(
            api_key=self.api_key,
            model=self.model
        )

class AzureOpenAIService(BaseLLMService):
    def __init__(
        self, 
        api_key: str,
        azure_endpoint: str,
        api_version: str,
        deployment_name: str
    ):
        self.api_key = api_key
        self.azure_endpoint = azure_endpoint
        self.api_version = api_version
        self.deployment_name = deployment_name

    def get_llm(self):
        return AzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.azure_endpoint,
            api_version=self.api_version,
            deployment_name=self.deployment_name
        )

class LLMServiceFactory:
    """Factory for creating LLM services"""
    
    @staticmethod
    def create_service(provider: str, config: Dict[str, Any]) -> BaseLLMService:
        if provider == "openai":
            return OpenAIService(
                api_key=config["api_key"],
                model=config.get("model", "gpt-4")
            )
        elif provider == "anthropic":
            return AnthropicService(
                api_key=config["api_key"],
                model=config.get("model", "claude-2")
            )
        elif provider == "cohere":
            return CohereService(
                api_key=config["api_key"],
                model=config.get("model", "command")
            )
        elif provider == "azure":
            return AzureOpenAIService(
                api_key=config["api_key"],
                azure_endpoint=config["azure_endpoint"],
                api_version=config["api_version"],
                deployment_name=config["deployment_name"]
            )
        elif provider == "nvidia":
            return NVIDIA(
                model=config.get("model", "microsoft/phi-3-small-128k-instruct"),
                api_key=config["api_key"]
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")