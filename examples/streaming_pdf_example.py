"""Example usage of streaming PDF loader for memory-efficient processing.

This example demonstrates how to use the streaming PDF loader to process
large PDF files with reduced memory footprint using Docling's page_range feature.
"""

from pathlib import Path
from app.ingestion.utils.streaming_pdf_loader import load_pdf_streaming


def example_basic_streaming():
    """Basic streaming example - process chunks as they arrive."""
    pdf_path = Path("large_document.pdf")

    print("Processing PDF with streaming loader...")

    for doc in load_pdf_streaming(pdf_path, chunk_pages=10):
        # Process each chunk immediately
        # Memory only holds current chunk, not entire PDF
        page_range = doc.metadata['page_range']
        total_pages = doc.metadata['total_pages']
        print(f"Processing pages {page_range}/{total_pages}")

        # Your processing logic here
        # e.g., extract entities, chunk text, store in vector DB
        process_document(doc)


def example_with_custom_chunk_size():
    """Use smaller chunks for very large PDFs or limited memory."""
    pdf_path = Path("huge_document.pdf")

    # Process only 5 pages at a time for maximum memory efficiency
    for doc in load_pdf_streaming(pdf_path, chunk_pages=5):
        print(f"Pages {doc.metadata['page_range']}: {len(doc.page_content)} chars")


def example_early_termination():
    """Stop processing early if condition is met."""
    pdf_path = Path("document.pdf")

    for doc in load_pdf_streaming(pdf_path):
        # Process until we find what we need
        if "target_keyword" in doc.page_content:
            print(f"Found keyword in pages {doc.metadata['page_range']}")
            break

        # No need to process remaining chunks


def example_batch_processing():
    """Collect documents in batches for bulk operations."""
    pdf_path = Path("document.pdf")
    batch_size = 20
    batch = []

    for doc in load_pdf_streaming(pdf_path, chunk_pages=10):
        batch.append(doc)

        # Process in batches of 20 documents
        if len(batch) >= batch_size:
            bulk_insert_to_database(batch)
            batch = []

    # Process remaining documents
    if batch:
        bulk_insert_to_database(batch)


def process_document(doc):
    """Placeholder for document processing logic."""
    # Your processing code here
    pass


def bulk_insert_to_database(docs):
    """Placeholder for bulk database insertion."""
    print(f"Inserting {len(docs)} documents to database")


if __name__ == "__main__":
    print("Streaming PDF Loader Examples")
    print("=" * 50)
    print()
    print("Benefits:")
    print("- 30-50% memory reduction for large PDFs")
    print("- Process 1000+ page documents")
    print("- Results available immediately")
    print("- Early termination support")
    print()
    print("How it works:")
    print("- Uses Docling's page_range parameter")
    print("- Converts PDF in chunks (e.g., 10 pages at a time)")
    print("- Each chunk is processed and released before loading next")
    print("- Peak memory scales with chunk_pages, not total pages")
    print()
    print("Note: Requires initial full conversion to get page count")
    print("See function implementations above for usage patterns.")

