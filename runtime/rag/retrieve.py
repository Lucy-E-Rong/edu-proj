from __future__ import annotations

from typing import Any, Dict, List

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHROMA_DIR = "chroma"
COLLECTION_NAME = "edu_chunks"
DEFAULT_TOP_K = 3


def retrieve(query: str, k: int = DEFAULT_TOP_K) -> List[Dict[str, Any]]:
    import chromadb
    from sentence_transformers import SentenceTransformer

    query = query.strip()
    if not query:
        return []

    k = DEFAULT_TOP_K

    embedder = SentenceTransformer(EMBEDDING_MODEL)
    query_embedding = embedder.encode(query).tolist()

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
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
            }
        )
    return output
