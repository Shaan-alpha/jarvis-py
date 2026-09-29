from core.memory.document_memory import (
    build_index
)

files, chunks = build_index()

print(f"Indexed {chunks} chunks from {files} PDFs." if files else "No PDFs found to index.")
