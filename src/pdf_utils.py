import os
import fitz
import uuid
from typing import List
import pymupdf4llm
import pymupdf
from streamlit import session_state as ss
from concurrent.futures import ThreadPoolExecutor
import logging

def process_pdf_chunk(chunk_data):
    """
    Process a chunk of PDF data
    """
    try:
        md_read = pymupdf4llm.LlamaMarkdownReader()
        return md_read.load_data(chunk_data)
    except Exception as e:
        logging.error(f"Error processing PDF chunk: {str(e)}")
        return None

def docs_from_pymupdf4llm(path: str, chunk_size: int = 10):
    """
    Process PDF in chunks using parallel processing
    Args:
        path: path to pdf file
        chunk_size: number of pages to process in each chunk
    """
    doc = fitz.open(path)
    total_pages = len(doc)
    chunks = []
    
    # Split document into chunks
    for i in range(0, total_pages, chunk_size):
        end = min(i + chunk_size, total_pages)
        chunks.append((path, i, end))
    
    # Process chunks in parallel
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(process_pdf_chunk, chunks))
    
    # Combine results
    combined_data = []
    for result in results:
        if result:
            combined_data.extend(result)
    
    return combined_data

def extract_images_text_pdf(
    path: str, image_path: str, export_images: bool = True, image_format: str = "jpg"
):
    """
    Extract text and images from a pdf file
    """
    return pymupdf4llm.to_markdown(
        doc=path,
        write_images=export_images,
        image_path=image_path,
        image_format=image_format,
    )

def extract_tables_from_pdf(path: str):
    """
    Extract tables from a pdf file
    """
    doc = pymupdf.open(path)
    tables = {}
    for i, page in enumerate(doc):
        tabs = page.find_tables()
        if len(tabs.tables) > 0:
            tables[i] = tabs
    return tables

def get_docs_to_add_vectorstore(pages, file, category="legal"):
    """
    Prepare documents for vector store in batches
    """
    documents = []
    ids = []
    metadatas = []

    for page in pages:
        metadatas.append({
            "page": page.metadata.get("page"),
            "filename": file,
            "category": category,
            "processed_date": str(uuid.uuid4())
        })
        ids.append(uuid.uuid1().hex)
        documents.append(page.page_content)

    return documents, ids, metadatas

def count_pdf_pages(pdf_path):
    """
    Count number of pages in a pdf file
    """
    doc = fitz.open(pdf_path)
    return len(doc)