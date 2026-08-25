# Resolution Context Sources

This directory contains the controlled text representations of the enterprise SOP and Knowledge Base used by the resolver-context retrieval pipeline.

- `sop_enterprise.txt` — controlled SOP source
- `kb_enterprise.txt` — controlled Knowledge Base source

The application indexes these documents as page-level chunks. The historical ticket corpus is built from resolved/closed tickets in `complaints.db`.

## Retrieval architecture

1. Dense semantic embedding with SentenceTransformers.
2. Sparse lexical retrieval with TF-IDF.
3. Reciprocal Rank Fusion (RRF).
4. Cross-encoder reranking.
5. Groq receives only the retrieved evidence plus the current ticket.

Rebuild the index after changing these documents or after adding a significant amount of historical ticket data:

```powershell
python rebuild_resolution_index.py
```
