import uuid
import hashlib
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from agno.knowledge.embedder.openai import OpenAIEmbedder

from app.models import Document, Chunk

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def simple_chunk_text(text: str, chunk_size: int = 1200, overlap: int = 150) -> list[str]:

    text = (text or "").strip()
    if not text:
        return []
    
    chunks: list[str] = []
    start = 0
    n = len(text)

    while start < n:
        end = min(start + chunk_size, n)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end == n:
            break

        start = max(0, end - overlap)

    return chunks

def ingest_text(
    db: Session,
    *,
    name: str,
    text: str,
    source_type: str = "text",
    source_uri: str | None = None,
    mime_type: str | None = "text/plain",
    metadata: dict[str, Any] | None = None,
    chunk_size: int = 1200,
    overlap: int = 200,
) -> uuid.UUID:

    metadata = metadata or {}

    checksum = _sha256(text)

    existing = (
        db.query(Document)
        .filter(Document.checksum == checksum)
        .one_or_none()
    )
    if existing:
        return existing.id

    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        name=name,
        source_type=source_type,
        source_uri=source_uri,
        mime_type=mime_type,
        checksum=checksum,
        status="pending",
        metadata=metadata,
    )
    db.add(doc)
    db.flush()

    chunks_text = simple_chunk_text(text, chunk_size=chunk_size, overlap=overlap)
    if not chunks_text:
        doc.status = "failed"
        db.commit()
        raise ValueError("Texto vazio após normalização/chunking.")

    embedder = OpenAIEmbedder() 

    for idx, chunk_str in enumerate(chunks_text):
        emb = embedder.get_embedding(chunk_str)

        ch = Chunk(
            id=uuid.uuid4(),
            document_id=doc_id,
            chunk_index=idx,
            content=chunk_str,
            token_count=None,
            embedding=emb,
            metadata={
                "chunk_size": chunk_size,
                "overlap": overlap,
            },
        )
        db.add(ch)

    doc.status = "processed"
    doc.processed_at = datetime.now(timezone.utc)

    db.commit()
    return doc_id