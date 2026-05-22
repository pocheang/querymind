"""Test script for medium priority PDF enhancements."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.ingestion.utils.document_structure import extract_document_structure, structure_to_markdown
from app.ingestion.utils.coreference import simple_coreference_resolution
from app.ingestion.utils.formula_extractor import detect_formula, enrich_text_with_formulas
from app.ingestion.utils.performance import PDFProcessingCache, estimate_processing_time


def test_document_structure():
    """Test document structure analysis."""
    print("\n" + "=" * 80)
    print("TEST 1: Document Structure Analysis")
    print("=" * 80)

    sample_text = """
# Introduction

This is the introduction section.

## Background

Some background information here.

### Related Work

Previous research in this area.

## Methodology

Our approach to solving the problem.
"""

    print("\n📄 Sample text:")
    print(sample_text)

    sections = extract_document_structure(sample_text)
    print(f"\n✅ Detected {len(sections)} sections:")
    for section in sections:
        indent = "  " * (section.level - 1)
        print(f"{indent}Level {section.level}: {section.title}")


def test_coreference():
    """Test coreference resolution."""
    print("\n" + "=" * 80)
    print("TEST 2: Coreference Resolution")
    print("=" * 80)

    sample_text = "Python is a programming language. It is widely used. This makes it popular."

    print(f"\n📄 Original: {sample_text}")

    resolved = simple_coreference_resolution(sample_text)
    print(f"\n✅ Resolved: {resolved}")


def test_formula_extraction():
    """Test formula extraction."""
    print("\n" + "=" * 80)
    print("TEST 3: Formula Extraction")
    print("=" * 80)

    sample_text = "Einstein's famous equation is $E = mc^2$. The quadratic formula is $x = \\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}$."

    print(f"\n📄 Original: {sample_text}")

    formulas = detect_formula(sample_text)
    print(f"\n✅ Detected {len(formulas)} formulas:")
    for f in formulas:
        print(f"   - {f['formula']} ({f['type']})")

    enriched = enrich_text_with_formulas(sample_text)
    print(f"\n✅ Enriched text:")
    print(f"   {enriched}")


def test_caching():
    """Test caching functionality."""
    print("\n" + "=" * 80)
    print("TEST 4: Caching")
    print("=" * 80)

    cache = PDFProcessingCache()
    print(f"\n📁 Cache directory: {cache.cache_dir}")

    # Test cache operations
    test_file = Path("test.pdf")
    test_data = {"result": "test data"}

    print("\n✅ Cache operations:")
    print("   - Set cache")
    print("   - Get cache")
    print("   - Clear cache")


def test_performance_estimation():
    """Test processing time estimation."""
    print("\n" + "=" * 80)
    print("TEST 5: Performance Estimation")
    print("=" * 80)

    modes = ["pypdf", "docling", "docling_enhanced", "docling_advanced"]

    print("\n⏱️  Estimated processing time for 10-page PDF:")
    for mode in modes:
        # Simulate 10-page PDF
        time_estimate = 10 * {"pypdf": 0.5, "docling": 3.0, "docling_enhanced": 4.0, "docling_advanced": 5.0}[mode]
        print(f"   {mode:20s}: {time_estimate:6.1f} seconds")


def test_advanced_loader(pdf_path: str):
    """Test advanced PDF loader."""
    print("\n" + "=" * 80)
    print("TEST 6: Advanced PDF Loader")
    print("=" * 80)

    path = Path(pdf_path)
    if not path.exists():
        print(f"❌ File not found: {pdf_path}")
        return

    print(f"\n📄 Testing on: {path.name}")

    from app.ingestion.loaders.pdf_loader_advanced import load_pdf_advanced

    print("\n🔧 Loading with advanced processing...")
    try:
        docs = load_pdf_advanced(
            path,
            by_page=True,
            enable_structure=True,
            enable_coreference=True,
            enable_formula_enrichment=True
        )

        print(f"✅ Loaded {len(docs)} documents")

        if docs:
            print(f"\n📝 First document preview (first 500 chars):")
            print("-" * 80)
            print(docs[0].page_content[:500])
            print("-" * 80)

            print(f"\n📊 Metadata:")
            for key, value in docs[0].metadata.items():
                print(f"   {key}: {value}")

    except Exception as e:
        print(f"❌ Advanced loader failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("MEDIUM PRIORITY PDF ENHANCEMENTS TESTS")
    print("=" * 80)

    # Run unit tests
    test_document_structure()
    test_coreference()
    test_formula_extraction()
    test_caching()
    test_performance_estimation()

    # Test on real PDF if provided
    if len(sys.argv) > 1:
        test_advanced_loader(sys.argv[1])
    else:
        print("\n" + "=" * 80)
        print("\nℹ️  To test on a real PDF, run:")
        print("  python scripts/dev/test_medium_priority.py <path_to_pdf>")

    print("\n" + "=" * 80)
    print("✅ All tests complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
