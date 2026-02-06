from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from transformers import AutoTokenizer


EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
CHROMA_DIR = "chroma"
COLLECTION_NAME = "edu_chunks"


@dataclass
class Chunk:
    chunk_id: int
    text: str


def _chunk_text_tokenwise(text: str) -> List[Chunk]:
    tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL)
    token_ids = tokenizer.encode(text, add_special_tokens=False)
    chunks: List[Chunk] = []
    step = CHUNK_SIZE - CHUNK_OVERLAP
    start = 0
    chunk_id = 0

    while start < len(token_ids):
        part = token_ids[start : start + CHUNK_SIZE]
        if not part:
            break
        decoded = tokenizer.decode(part, skip_special_tokens=True).strip()
        if decoded:
            chunks.append(Chunk(chunk_id=chunk_id, text=decoded))
            chunk_id += 1
        start += step

    return chunks


def ingest_textbook(
    source_path: str = "assets/mock_textbook.txt",
    chroma_dir: str = CHROMA_DIR,
    collection_name: str = COLLECTION_NAME,
) -> int:
    import chromadb
    from sentence_transformers import SentenceTransformer

    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    text = source.read_text(encoding="utf-8")
    chunks = _chunk_text_tokenwise(text)
    if not chunks:
        raise ValueError("No chunks produced from source text")

    model = SentenceTransformer(EMBEDDING_MODEL)
    texts = [c.text for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=False).tolist()

    client = chromadb.PersistentClient(path=chroma_dir)
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    ids = [f"chunk-{c.chunk_id}" for c in chunks]
    metadatas = [{"source": str(source), "chunk_id": c.chunk_id} for c in chunks]

    existing = collection.get(ids=ids)
    existing_ids = set(existing.get("ids", []))

    add_ids, add_docs, add_metas, add_embs = [], [], [], []
    for idx, cid in enumerate(ids):
        if cid in existing_ids:
            continue
        add_ids.append(cid)
        add_docs.append(texts[idx])
        add_metas.append(metadatas[idx])
        add_embs.append(embeddings[idx])

    if add_ids:
        collection.add(ids=add_ids, documents=add_docs, metadatas=add_metas, embeddings=add_embs)

    return len(chunks)
