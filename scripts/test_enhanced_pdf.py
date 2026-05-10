"""Test script for enhanced PDF processing features."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.ingestion.utils.pdf_cleaner import detect_repeated_patterns, clean_pdf_pages
from app.ingestion.utils.table_merger import detect_incomplete_table, merge_cross_page_tables
from app.ingestion.utils.nested_table_handler import detect_nested_table, simplify_complex_table
from app.ingestion.loaders.pdf_loader import load_pdf_enhanced, load_pdf_with_docling


def test_header_footer_removal():
    """Test header/footer detection and removal."""
    print("\n" + "=" * 80)
    print("TEST 1: Header/Footer Removal")
    print("=" * 80)

    # Simulate pages with repeated headers/footers
    pages = [
        "Company Confidential - Page 1\nActual content here\nFooter text",
        "Company Confidential - Page 2\nMore content\nFooter text",
        "Company Confidential - Page 3\nEven more content\nFooter text",
    ]

    print("\n📄 Original pages:")
    for i, page in enumerate(pages, 1):
        print(f"\nPage {i}:\n{page}")

    # Detect repeated patterns
    repeated = detect_repeated_patterns(pages)
    print(f"\n🔍 Detected repeated patterns: {repeated}")

    # Clean pages
    cleaned = clean_pdf_pages(pages)
    print("\n✨ Cleaned pages:")
    for i, page in enumerate(cleaned, 1):
        print(f"\nPage {i}:\n{page}")


def test_cross_page_table_merging():
    """Test cross-page table merging."""
    print("\n" + "=" * 80)
    print("TEST 2: Cross-Page Table Merging")
    print("=" * 80)

    # Simulate table split across pages
    page1 = """
# Report

| Product | Price | Stock |
|---------|-------|-------|
| Item A  | $100  | 50    |
| Item B  | $200  | 30    |
"""

    page2 = """
| Item C  | $150  | 40    |
| Item D  | $250  | 20    |

End of table.
"""

    pages = [page1, page2]

    print("\n📄 Original pages:")
    print(f"Page 1:\n{page1}")
    print(f"Page 2:\n{page2}")

    # Check if table is incomplete
    is_incomplete = detect_incomplete_table(page1)
    print(f"\n🔍 Page 1 has incomplete table: {is_incomplete}")

    # Merge tables
    merged = merge_cross_page_tables(pages)
    print(f"\n✨ Merged into {len(merged)} page(s):")
    for i, page in enumerate(merged, 1):
        print(f"\nPage {i}:\n{page}")


def test_nested_table_handling():
    """Test nested table detection and flattening."""
    print("\n" + "=" * 80)
    print("TEST 3: Nested Table Handling")
    print("=" * 80)

    # Simulate nested table
    nested_table = """
| Category | Details |
|----------|---------|
| Products | Item A | $100 | Item B | $200 |
| Services | Service X | $50 | Service Y | $75 |
"""

    print("\n📄 Original table with nested content:")
    print(nested_table)

    # Detect nested table
    is_nested = detect_nested_table(nested_table)
    print(f"\n🔍 Nested table detected: {is_nested}")

    # Simplify
    simplified = simplify_complex_table(nested_table)
    print("\n✨ Simplified table:")
    print(simplified)


def test_enhanced_loader(pdf_path: str):
    """Test enhanced PDF loader on real file."""
    print("\n" + "=" * 80)
    print("TEST 4: Enhanced PDF Loader")
    print("=" * 80)

    path = Path(pdf_path)
    if not path.exists():
        print(f"❌ File not found: {pdf_path}")
        return

    print(f"\n📄 Testing on: {path.name}")

    # Load with regular Docling
    print("\n🔧 Loading with regular Docling...")
    try:
        regular_docs = load_pdf_with_docling(path, by_page=True)
        print(f"✅ Regular Docling: {len(regular_docs)} pages")
        if regular_docs:
            print(f"\n📝 First page preview (first 300 chars):")
            print("-" * 80)
            print(regular_docs[0].page_content[:300])
            print("-" * 80)
    except Exception as e:
        print(f"❌ Regular Docling failed: {e}")

    # Load with enhanced processing
    print("\n🔧 Loading with enhanced processing...")
    try:
        enhanced_docs = load_pdf_enhanced(path, by_page=True)
        print(f"✅ Enhanced loader: {len(enhanced_docs)} pages")
        if enhanced_docs:
            print(f"\n📝 First page preview (first 300 chars):")
            print("-" * 80)
            print(enhanced_docs[0].page_content[:300])
            print("-" * 80)

            # Check metadata
            print(f"\n📊 Metadata: {enhanced_docs[0].metadata}")
    except Exception as e:
        print(f"❌ Enhanced loader failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("PDF ENHANCED PROCESSING TESTS")
    print("=" * 80)

    # Run unit tests
    test_header_footer_removal()
    test_cross_page_table_merging()
    test_nested_table_handling()

    # Test on real PDF if provided
    if len(sys.argv) > 1:
        test_enhanced_loader(sys.argv[1])
    else:
        print("\n" + "=" * 80)
        print("\nℹ️  To test on a real PDF, run:")
        print("  python scripts/test_enhanced_pdf.py <path_to_pdf>")

    print("\n" + "=" * 80)
    print("✅ All tests complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
