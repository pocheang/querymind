# Demo Dataset Setup

The demo dataset files are not committed to git (data/ is in .gitignore).

## Quick Setup

Run the setup script to create all demo documents:

```bash
python scripts/setup_demo_dataset.py
```

This will create:
- `data/demo/enterprise/` - Enterprise documents (HR, IT, Finance)
- `data/demo/technical/` - Technical documents (RAG, FastAPI, LangGraph)
- `data/demo/evaluation/` - Test queries and ground truth

## Manual Setup

If you prefer to create the files manually, the demo dataset content was
sourced from an internal plan document (now archived in `internal_docs/plans/`).
Contact the maintainers for the full content.

## Ingesting Documents

After creating the demo documents, ingest them into the vector store:

```bash
python scripts/ingest_demo_data.py
```

## Running Evaluation

Once documents are ingested, run the evaluation:

```bash
python scripts/run_evaluation.py
```

This will evaluate all baseline systems and save results to `data/evaluation/results/`.
