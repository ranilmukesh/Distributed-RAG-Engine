from fastapi import FastAPI, BackgroundTasks
from typing import List

app = FastAPI()
processor = DistributedPDFProcessor()
monitor = ProcessingMonitor()

@app.post("/batch-process")
async def batch_process_pdfs(
    pdf_paths: List[str],
    background_tasks: BackgroundTasks
):
    """API endpoint for batch processing"""
    background_tasks.add_task(
        processor.process_pdf_batch,
        pdf_paths
    )
    return {"status": "processing_started"}

@app.get("/status/{batch_id}")
async def get_batch_status(batch_id: str):
    """Check processing status"""
    return await processor.get_batch_status(batch_id) 