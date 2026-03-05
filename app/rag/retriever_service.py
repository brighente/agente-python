import uuid
from typing import Any

from sqlalchemy.orm import Session
from agno.knowledge.embedder.openai import OpenAIEmbedder
from app.models import Chunk, Document
from dataclasses import dataclass
@dataclass

class RetrievedChunk:
    chunk_id: str
    document_id: str
    document_name: str
    content: str
    score: float
    metadata: dict[str, Any]

def retrieve_top_k(
    db: Session,
    query: str,
    top_k: int = 5,
    filters: dict[str, Any] | None = None,
) -> list[RetrievedChunk]:
    embedder = OpenAIEmbedder()
    q_emb = embedder.get_embedding(query)

    q = (
        db.query(
            Chunk,
            Document,
            Chunk.embedding.cosine_distance(q_emb).label("distance"),
        )
        .join(Document, Document.id == Chunk.document_id)
        .filter(Document.status == "processed")
    )

    if filters:
        doc_id = filters.get("document_id")
        if doc_id:
            q = q.filter(Chunk.document_id == uuid.UUID(doc_id))

        doc_meta = filters.get("doc_metadata")
        if isinstance(doc_meta, dict):
            for key, val in doc_meta.items():
                q = q.filter(Document.metadata[key].astext == str(val))

    rows = (
        q.order_by("distance")
        .limit(top_k)
        .all()
    )

    results: list[RetrievedChunk] = []
    for chunk, doc, distance in rows:
        score = float(1.0 - distance) if distance is not None else 0.0
        results.append(
            RetrievedChunk(
                chunk_id=str(chunk.id),
                document_id=str(doc.id),
                document_name=getattr(doc, "name", None) or "",
                content=chunk.content,
                score=score,
                metadata={
                    "chunk": chunk.metadata or {},
                    "document": doc.metadata or {},
                },
            )
        )
    return results