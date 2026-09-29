# data/documents/

Drop any PDFs you want Jarvis to be able to answer questions about into
this folder, then run:

```bash
python build_memory.py
```

This will chunk the PDFs, embed them with `fastembed`, and persist a
FAISS index at `data/vector.index` + `data/chunks.pkl`.

Both the source PDFs and the generated index/chunks are gitignored —
nothing in here is ever committed.

## Tips

- Re-run `build_memory.py` whenever you add, remove, or update a PDF.
- The retrieval threshold is `DOCUMENT_SIMILARITY_THRESHOLD` in
  `config/settings.py` (default `0.6`). Lower → more chunks injected
  into the LLM prompt; higher → only very relevant chunks.
- If results feel noisy, raise the threshold to `0.55–0.65`.
