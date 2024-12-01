from llama_index.core import StorageContext, load_index_from_storage
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
import os

def get_vector_store(collection_name: str, url: str = None, api_key: str = None):
    """
    Get or create a Qdrant vector store
    """
    if url and api_key:
        client = QdrantClient(url=url, api_key=api_key)
    else:
        # Local instance for development
        client = QdrantClient(path="./qdrant_data")
    
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=collection_name
    )
    return vector_store

def load_index_from_disk(path: str):
    """
    Load index from disk
    """
    storage_context = StorageContext.from_defaults(persist_dir=path)
    index = load_index_from_storage(storage_context)
    return index

def persist_index_to_disk(index, path: str):
    """
    Persist index to disk
    """
    index.storage_context.persist(path)
    return

def batch_process_documents(documents, batch_size=100):
    """
    Process documents in batches to manage memory
    """
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        yield batch