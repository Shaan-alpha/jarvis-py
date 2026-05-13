# models/embeddings/

`fastembed` caches the `sentence-transformers/all-MiniLM-L6-v2` ONNX
model here on first use (~90 MB). Configured via `CACHE_DIR` in
`core/memory/embedder.py`.

You don't need to do anything — first call to `encode()` downloads
the model. Subsequent runs load from this cache.

Gitignored; nothing here is committed.
