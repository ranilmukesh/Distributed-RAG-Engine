from llama_index.vector_stores import ChromaVectorStore
from llama_index.storage.storage_context import StorageContext
from chromadb import PersistentClient
import os

class ScalableVectorStore:
    def __init__(self, persist_dir="./data/chroma_db"):
        """Initialize with persistent storage"""
        self.persist_dir = persist_dir
        os.makedirs(persist_dir, exist_ok=True)
        self.chroma_client = PersistentClient(path=persist_dir)
        
    def create_or_load_collection(self, collection_name):
        """Create or load existing collection"""
        chroma_collection = self.chroma_client.get_or_create_collection(
            name=collection_name
        )
        vector_store = ChromaVectorStore(
            chroma_collection=chroma_collection
        )
        storage_context = StorageContext.from_defaults(
            vector_store=vector_store
        )
        return storage_context

    async def batch_process_documents(self, documents, batch_size=100):
        """Process documents in batches"""
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            index = VectorStoreIndex.from_documents(
                batch,
                storage_context=self.storage_context,
                show_progress=True
            )
            await index.storage_context.persist() 