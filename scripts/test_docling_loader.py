"""Test script for Docling PDF loader integration."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.ingestion.loaders.pdf_loader import load_pdf_with_docling, load_pdf_text


def test_docling_loader(pdf_path: str):
    """Test Docling loader on a PDF file."""
    path = Path(pdf_path)

    if not path.exists():
        print(f"❌ File not found: {pdf_path}")
        return

    print(f"📄 Testing Docling on: {path.name}\n")
    print("=" * 80)

    # Test Docling loader
    print("\n🔧 Loading with Docling (Markdown mode)...")
    try:
        docling_docs = load_pdf_with_docling(path, by_page=True)
        print(f"✅ Docling loaded {len(docling_docs)} pages")

        if docling_docs:
            print(f"\n📝 First page preview (first 500 chars):")
            print("-" * 80)
            print(docling_docs[0].page_content[:500])
            print("-" * 80)

            # Check for Markdown tables
            has_tables = any("|" in doc.page_content for doc in docling_docs)
            if has_tables:
                print("\n✅ Markdown tables detected!")
                for i, doc in enumerate(docling_docs, 1):
                    if "|" in doc.page_content:
                        print(f"\n📊 Table found on page {i}:")
                        # Show first table
                        lines = doc.page_content.split("\n")
                        table_lines = [line for line in lines if "|" in line][:5]
                        for line in table_lines:
                            print(f"  {line}")
                        break
            else:
                print("\nℹ️  No Markdown tables detected in this PDF")

    except Exception as e:
        print(f"❌ Docling failed: {e}")
        import traceback
        traceback.print_exc()

    # Compare with PyPDF
    print("\n" + "=" * 80)
    print("\n🔧 Loading with PyPDF (traditional mode)...")
    try:
        pypdf_docs = load_pdf_text(path)
        print(f"✅ PyPDF loaded {len(pypdf_docs)} pages")

        if pypdf_docs:
            print(f"\n📝 First page preview (first 500 chars):")
            print("-" * 80)
            print(pypdf_docs[0].page_content[:500])
            print("-" * 80)
    except Exception as e:
        print(f"❌ PyPDF failed: {e}")

    print("\n" + "=" * 80)
    print("\n✅ Test complete!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_docling_loader.py <path_to_pdf>")
        print("\nExample:")
        print("  python scripts/test_docling_loader.py data/docs/sample.pdf")
        sys.exit(1)

    test_docling_loader(sys.argv[1])
