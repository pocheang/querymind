# scripts/dev/

Manual smoke and developer-driven verification scripts.

These are **not** pytest tests. They are CLI tools intended to be run by a
developer against a real environment (a real PDF, a running database, an
actual API key) to spot-check end-to-end behaviour. Automated tests live in
`tests/`.

## When to use

- Verifying an integration end-to-end (Docling, OCR, chart extraction)
- Quickly testing a new pipeline change with a real document
- Resetting or sanity-checking admin user state on a local install

## Available scripts

| Script | Purpose |
| --- | --- |
| `test_and_reset_admin.py` | Verify admin login and reset password if needed |
| `test_chart_extraction.py` | Smoke-test chart extraction on a PDF |
| `test_docling_loader.py` | Smoke-test the Docling PDF loader |
| `test_enhanced_pdf.py` | Run enhanced-PDF feature checks |
| `test_intent_classifier.py` | Sanity-check the LLM intent classifier |
| `test_layout_vs_text.py` | Compare layout-based vs text-based structure detection |
| `test_medium_priority.py` | Smoke-test medium-priority PDF features |
| `test_ocr_integration.py` | Smoke-test OCR integration against a real PDF |
| `test_query_rewriter.py` | Sanity-check the query rewriter output |

## Conventions

- Each script is a runnable CLI; pass `--help` or read the top of the file for usage
- Scripts may require API keys, a running backend, or specific data files
- Output is for human inspection; failures here do not necessarily mean broken
  code (often they indicate environment issues)
