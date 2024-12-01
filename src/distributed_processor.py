from concurrent.futures import ThreadPoolExecutor
import asyncio
from typing import List, Dict, Optional
import pandas as pd
import logging
from redis import Redis
from motor.motor_asyncio import AsyncIOMotorClient

class EnterpriseDocumentProcessor:
    def __init__(self, config: dict):
        """
        Initialize enterprise document processor
        Args:
            config: Configuration dictionary containing:
                - redis_url: Redis connection URL
                - mongodb_url: MongoDB connection URL
                - max_workers: Maximum number of worker threads
                - batch_size: Size of processing batches
        """
        self.max_workers = config.get('max_workers', 4)
        self.batch_size = config.get('batch_size', 100)
        
        # Initialize Redis for job queue
        self.redis = Redis.from_url(config['redis_url'])
        
        # Initialize MongoDB for metadata
        self.mongo = AsyncIOMotorClient(config['mongodb_url'])
        self.db = self.mongo.documents
        
        # Initialize metrics
        self.metrics = {
            'docs_processed': 0,
            'processing_errors': 0,
            'processing_time': 0
        }

    async def process_documents(self, documents: List[str]) -> Dict:
        """
        Process documents with enterprise features
        """
        try:
            # Document fingerprinting
            doc_hashes = await self._generate_document_hashes(documents)
            
            # Duplicate detection
            unique_docs = await self._filter_duplicates(documents, doc_hashes)
            
            # Batch processing with monitoring
            results = await self._batch_process(unique_docs)
            
            # Store metadata
            await self._store_metadata(results)
            
            return {
                'status': 'success',
                'processed': len(results),
                'metrics': self.metrics
            }
            
        except Exception as e:
            logging.error(f"Document processing failed: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    async def _batch_process(self, documents: List[str]) -> List[Dict]:
        """
        Process documents in batches
        """
        results = []
        for i in range(0, len(documents), self.batch_size):
            batch = documents[i:i + self.batch_size]
            batch_results = await self._process_batch(batch)
            results.extend(batch_results)
        return results
    
    async def _process_batch(self, pdf_paths: List[str]) -> Dict:
        """Process a batch of PDFs concurrently"""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [
                executor.submit(self._process_single_pdf, path)
                for path in pdf_paths
            ]
            results = [f.result() for f in futures]
        return results
    
    def _process_single_pdf(self, pdf_path: str):
        """Process individual PDF with error handling"""
        try:
            docs = docs_from_pymupdf4llm(pdf_path)
            metadata = {
                'filename': os.path.basename(pdf_path),
                'processed_at': pd.Timestamp.now().isoformat()
            }
            return {'status': 'success', 'docs': docs, 'metadata': metadata}
        except Exception as e:
            return {'status': 'error', 'path': pdf_path, 'error': str(e)} 

class PerformanceOptimizer:
    def __init__(self, config: Dict):
        """Initialize performance optimizer"""
        self.redis = Redis.from_url(config.get('REDIS_URL', 'redis://localhost:6379'))
        self.max_workers = config.get('MAX_WORKERS', 4)
        self.batch_size = config.get('BATCH_SIZE', 100)
        self.cache_ttl = config.get('CACHE_TTL', 3600)  # 1 hour default
        self.processing_queue = queue.Queue()
        self.thread_pool = ThreadPoolExecutor(max_workers=self.max_workers)
        
    def batch_process_documents(self, documents: List[str]) -> List[Dict]:
        """Process documents in optimized batches"""
        results = []
        total_docs = len(documents)
        
        for i in range(0, total_docs, self.batch_size):
            batch = documents[i:i + self.batch_size]
            batch_size_metric.observe(len(batch))
            
            with processing_time.time():
                batch_results = self._process_batch(batch)
                results.extend(batch_results)
                
        return results
    
    def _process_batch(self, batch: List[str]) -> List[Dict]:
        """Process a single batch with optimizations"""
        futures = []
        results = []
        
        # Check cache first
        cached_results = self._get_cached_results(batch)
        results.extend(cached_results['found'])
        
        # Process only uncached documents
        for doc in cached_results['not_found']:
            future = self.thread_pool.submit(self._process_single_document, doc)
            futures.append(future)
            
        # Collect results
        for future in futures:
            try:
                result = future.result(timeout=30)
                results.append(result)
                # Cache the new result
                self._cache_result(result['id'], result)
            except Exception as e:
                logging.error(f"Batch processing error: {str(e)}")
                
        return results
    
    def _get_cached_results(self, documents: List[str]) -> Dict:
        """Check cache for existing results"""
        found = []
        not_found = []
        
        for doc in documents:
            cache_key = f"doc_result:{doc}"
            cached = self.redis.get(cache_key)
            
            if cached:
                cache_hits.inc()
                found.append(cached)
            else:
                cache_misses.inc()
                not_found.append(doc)
                
        return {
            'found': found,
            'not_found': not_found
        }
    
    def _cache_result(self, doc_id: str, result: Dict):
        """Cache processed result"""
        cache_key = f"doc_result:{doc_id}"
        self.redis.setex(cache_key, self.cache_ttl, str(result))
    
    def _process_single_document(self, document: str) -> Dict:
        """Process a single document with optimizations"""
        try:
            # Add your document processing logic here
            # This is just a placeholder
            result = {
                'id': document,
                'status': 'processed',
                'timestamp': time.time()
            }
            return result
        except Exception as e:
            logging.error(f"Document processing error: {str(e)}")
            return {
                'id': document,
                'status': 'error',
                'error': str(e)
            }

    def optimize_connection_pool(self):
        """Optimize connection pool settings"""
        self.redis.connection_pool.max_connections = self.max_workers * 2
        
    def get_performance_metrics(self) -> Dict:
        """Get current performance metrics"""
        return {
            'cache_hit_rate': cache_hits._value / (cache_hits._value + cache_misses._value) if (cache_hits._value + cache_misses._value) > 0 else 0,
            'active_workers': threading.active_count(),
            'queue_size': self.processing_queue.qsize(),
        }