from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

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


@dataclass
class SourceDoc:
    path: Path
    text: str
    metadata: Dict[str, str]


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


def _strip_leading_frontmatter(text: str) -> tuple[Dict[str, str], str]:
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return {}, text

    metadata: Dict[str, str] = {}
    end_idx = -1
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_idx = idx
            break
        if ":" in lines[idx]:
            key, value = lines[idx].split(":", 1)
            metadata[key.strip()] = value.strip().strip('"')

    if end_idx == -1:
        return {}, text

    cleaned = "\n".join(lines[end_idx + 1 :]).strip()
    return metadata, cleaned


def _infer_doc_type(path: Path) -> str:
    name = path.name.lower()
    if name.startswith("cve-"):
        return "cve"
    return path.stem.lower()


def _module_id(path: Path) -> str:
    for part in path.parts:
        if re.fullmatch(r"module_\d+", part):
            return part
    return "n/a"


def _build_source_doc(path: Path) -> SourceDoc:
    raw = path.read_text(encoding="utf-8")
    frontmatter, cleaned = _strip_leading_frontmatter(raw)
    metadata: Dict[str, str] = {
        "source": str(path),
        "module_id": _module_id(path),
        "doc_type": _infer_doc_type(path),
        "title": frontmatter.get("title", ""),
        "course": frontmatter.get("course", ""),
    }
    return SourceDoc(path=path, text=cleaned or raw, metadata=metadata)


def _index_docs(
    docs: Sequence[SourceDoc],
    chroma_dir: str,
    collection_name: str,
) -> int:
    import chromadb
    from sentence_transformers import SentenceTransformer

    all_texts: List[str] = []
    all_metas: List[Dict[str, str | int]] = []
    all_ids: List[str] = []

    for doc in docs:
        chunks = _chunk_text_tokenwise(doc.text)
        for chunk in chunks:
            fingerprint = hashlib.md5(str(doc.path).encode("utf-8")).hexdigest()[:12]
            all_ids.append(f"{fingerprint}-chunk-{chunk.chunk_id}")
            all_texts.append(chunk.text)
            all_metas.append(
                {
                    **doc.metadata,
                    "chunk_id": chunk.chunk_id,
                }
            )

    if not all_texts:
        raise ValueError("No chunks produced from provided sources")

    model = SentenceTransformer(EMBEDDING_MODEL)
    embeddings = model.encode(all_texts, show_progress_bar=False).tolist()

    client = chromadb.PersistentClient(path=chroma_dir)
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    existing = collection.get(ids=all_ids)
    existing_ids = set(existing.get("ids", []))

    add_ids: List[str] = []
    add_docs: List[str] = []
    add_metas: List[Dict[str, str | int]] = []
    add_embs: List[List[float]] = []
    for idx, cid in enumerate(all_ids):
        if cid in existing_ids:
            continue
        add_ids.append(cid)
        add_docs.append(all_texts[idx])
        add_metas.append(all_metas[idx])
        add_embs.append(embeddings[idx])

    if add_ids:
        collection.add(ids=add_ids, documents=add_docs, metadatas=add_metas, embeddings=add_embs)

    return len(all_texts)


def ingest_textbook(
    source_path: str = "assets/mock_textbook.txt",
    chroma_dir: str = CHROMA_DIR,
    collection_name: str = COLLECTION_NAME,
) -> int:
    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")
    doc = SourceDoc(
        path=source,
        text=source.read_text(encoding="utf-8"),
        metadata={
            "source": str(source),
            "module_id": "n/a",
            "doc_type": "textbook",
            "title": "",
            "course": "",
        },
    )
    return _index_docs([doc], chroma_dir=chroma_dir, collection_name=collection_name)


def ingest_markdown_corpus(
    source_glob: str = "generated_modules/**/*.md",
    chroma_dir: str = CHROMA_DIR,
    collection_name: str = COLLECTION_NAME,
) -> int:
    paths = sorted(Path(".").glob(source_glob))
    files = [p for p in paths if p.is_file()]
    if not files:
        raise FileNotFoundError(f"No files matched glob: {source_glob}")

    docs = [_build_source_doc(path) for path in files]
    return _index_docs(docs, chroma_dir=chroma_dir, collection_name=collection_name)
