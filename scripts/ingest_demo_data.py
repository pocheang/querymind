"""
Ingest demo documents into the vector store.

This script ingests all documents from data/demo/ directory
for evaluation purposes.
"""

import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ingest_demo_documents():
    """Ingest all demo documents."""
    demo_dir = Path("data/demo")

    # Find all markdown files
    enterprise_docs = list((demo_dir / "enterprise").glob("*.md"))
    technical_docs = list((demo_dir / "technical").glob("*.md"))

    all_docs = enterprise_docs + technical_docs

    logger.info(f"Found {len(all_docs)} documents to ingest")
    logger.info(f"  Enterprise: {len(enterprise_docs)}")
    logger.info(f"  Technical: {len(technical_docs)}")

    # Import ingestion function
    try:
        from app.ingestion.ingest_file import ingest_file
    except ImportError:
        logger.error("Could not import ingest_file. Make sure the app is properly installed.")
        return

    # Ingest each document
    for doc_path in all_docs:
        logger.info(f"Ingesting: {doc_path.name}")
        try:
            ingest_file(str(doc_path))
            logger.info(f"  ✓ Successfully ingested {doc_path.name}")
        except Exception as e:
            logger.error(f"  ✗ Error ingesting {doc_path.name}: {e}")

    logger.info("\nIngestion complete!")


if __name__ == "__main__":
    ingest_demo_documents()
