from __future__ import annotations

from typing import Any, Dict, List

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHROMA_DIR = "chroma"
COLLECTION_NAME = "edu_chunks"
DEFAULT_TOP_K = 3


def _query_collection(query: str, collection_name: str, k: int) -> List[Dict[str, Any]]:
    import chromadb
    from sentence_transformers import SentenceTransformer

    query = query.strip()
    if not query:
        return []

    embedder = SentenceTransformer(EMBEDDING_MODEL)
    query_embedding = embedder.encode(query).tolist()

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    docs = result.get("documents", [[]])[0]
    metas = result.get("metadatas", [[]])[0]
    dists = result.get("distances", [[]])[0]

    output: List[Dict[str, Any]] = []
    for doc, meta, dist in zip(docs, metas, dists):
        output.append(
            {
                "text": doc,
                "source": (meta or {}).get("source", "unknown"),
                "chunk_id": (meta or {}).get("chunk_id", "n/a"),
                "distance": dist,
                "collection": collection_name,
            }
        )
    return output


def retrieve(query: str, k: int = DEFAULT_TOP_K, collection_name: str = COLLECTION_NAME) -> List[Dict[str, Any]]:
    return _query_collection(query=query, collection_name=collection_name, k=k)


def retrieve_teacher_first(
    query: str,
    teacher_collection: str,
    general_collection: str,
    teacher_k: int = DEFAULT_TOP_K,
    fallback_k: int = 2,
) -> List[Dict[str, Any]]:
    primary = _query_collection(query=query, collection_name=teacher_collection, k=teacher_k)
    if len(primary) >= teacher_k or fallback_k <= 0:
        return primary

    seen = {(item["source"], item["chunk_id"]) for item in primary}
    fallback = _query_collection(query=query, collection_name=general_collection, k=fallback_k)
    merged = list(primary)
    for item in fallback:
        key = (item["source"], item["chunk_id"])
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged
