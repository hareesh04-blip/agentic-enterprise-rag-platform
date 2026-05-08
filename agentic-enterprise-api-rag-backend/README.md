# Agentic Enterprise API RAG Backend

## Local test note (DOCX ingestion quality)

If `pytest` is not available in your environment, install it first:

```bash
pip install pytest
```

Run the DOCX ingestion quality tests:

```bash
set PYTHONPATH=. && python -m pytest tests/test_docx_ingestion_quality.py -q
```
