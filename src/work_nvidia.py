# test run and see that you can genreate a respond successfully

import os
from llama_index.llms.nvidia import NVIDIA
from llama_index.embeddings.nvidia import NVIDIAEmbedding
import logging
from llama_index.core import VectorStoreIndex
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.chat_engine import CondensePlusContextChatEngine
from llama_index.core import Settings
from llama_index.llms.openai import OpenAI
from llama_index.llms.anthropic import Anthropic
from llama_index.llms.azure_openai import AzureOpenAI
from typing import Literal

TEXT_SPLITTER_CHUNCK_SIZE = 200
TEXT_SPLITTER_CHUNCK_OVERLAP = 50

LLMTypes = Literal["openai", "claude", "azure"]

def get_llm(provider: LLMTypes, model: str = None, **kwargs):
    """
    Get LLM based on provider
    Args:
        provider: LLM provider (openai, claude, azure)
        model: Model name (optional)
        **kwargs: Additional arguments for the LLM
    """
    if provider == "openai":
        return OpenAI(
            model=model or "gpt-4-turbo-preview",
            temperature=kwargs.get('temperature', 0.7),
            max_tokens=kwargs.get('max_tokens', 1024)
        )
    
    elif provider == "claude":
        return Anthropic(
            model=model or "claude-3-sonnet-20240229",
            temperature=kwargs.get('temperature', 0.7),
            max_tokens=kwargs.get('max_tokens', 1024)
        )
    
    elif provider == "azure":
        return AzureOpenAI(
            model=model,
            deployment_name=kwargs.get('deployment_name'),
            api_base=kwargs.get('api_base'),
            api_key=kwargs.get('api_key'),
            api_version=kwargs.get('api_version', "2024-02-15-preview"),
            temperature=kwargs.get('temperature', 0.7),
            max_tokens=kwargs.get('max_tokens', 1024)
        )
    
    raise ValueError(f"Unsupported LLM provider: {provider}")


def get_embeddings(model):
    return NVIDIAEmbedding(model=model, truncate="END")


def setup_index(model, embeddings):
    """
    Args:
        model: str
        embeddings: str
    """
    Settings.llm = model
    Settings.embed_model = embeddings
    return


def vectorindex_from_data(data, embed_model):
    """
    Args:
        data: data. list of LLamaIndex Documents
    """
    index = VectorStoreIndex(data, embed_model=embed_model)
    return index


def create_memory_buffer(token_limit: int = 4500):
    """
    Create a memory buffer
    args:
        token_limit: int

    """
    return ChatMemoryBuffer.from_defaults(token_limit=token_limit)


def create_chat_engine(index):
    """
    create a chat engine
    Args:
        index: llama_index.core.VectorStoreIndex
    """
    memory = create_memory_buffer()
    return CondensePlusContextChatEngine.from_defaults(
        index.as_retriever(), memory=memory
    )
