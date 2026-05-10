"""Advanced PDF loader with all enhancements integrated."""

from pathlib import Path
from typing import List

from langchain_core.documents import Document

from app.ingestion.loaders.pdf_loader_enhanced import load_pdf_enhanced
from app.ingestion.utils.document_structure import extract_document_structure, add_section_metadata
from app.ingestion.utils.coreference import simple_coreference_resolution
from app.ingestion.utils.formula_extractor import enrich_text_with_formulas


def load_pdf_advanced(
    path: Path,
    by_page: bool = True,
    enable_structure: bool = True,
    enable_coreference: bool = True,
    enable_formula_enrichment: bool = True
) -> List[Document]:
    """
    Load PDF with all advanced processing features.

    Features:
    - Document structure analysis (chapters, sections)
    - Coreference resolution (pronoun resolution)
    - Formula semantic extraction
    - All previous enhancements (cleaning, table merging, etc.)

    Args:
        path: Path to PDF file
        by_page: Return one Document per page
        enable_structure: Enable document structure analysis
        enable_coreference: Enable coreference resolution
        enable_formula_enrichment: Enable formula semantic extraction

    Returns:
        List of Document objects with advanced processing
    """
    # Load with enhanced processing (cleaning, tables, etc.)
    docs = load_pdf_enhanced(path, by_page=by_page)

    if not docs:
        return docs

    # Process each document
    processed_docs = []

    for doc in docs:
        content = doc.page_content
        metadata = doc.metadata.copy()

        # Step 1: Formula enrichment
        if enable_formula_enrichment:
            content = enrich_text_with_formulas(content)
            metadata['formula_enrichment'] = True

        # Step 2: Coreference resolution
        if enable_coreference:
            content = simple_coreference_resolution(content)
            metadata['coreference_resolved'] = True

        # Step 3: Document structure
        if enable_structure:
            sections = extract_document_structure(content, page=metadata.get('page'))
            if sections:
                content = add_section_metadata(content, sections)
                metadata['sections_count'] = len(sections)
                metadata['has_structure'] = True

        # Create processed document
        processed_doc = Document(
            page_content=content,
            metadata=metadata
        )
        processed_docs.append(processed_doc)

    return processed_docs
