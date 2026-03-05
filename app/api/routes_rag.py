import hashlib
from typing import Any
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.rag.pdf_service import extract_text_from_pdf_bytes
from app.rag.retriever_service import retrieve_top_k
from app.schemas import IngestTextIn, IngestTextOut, RagHitOut, RagSearchIn, RagSearchOut, IngestPdfOut
from app.rag.ingest_service import ingest_text


router = APIRouter(prefix="/rag", tags=["rag"])

@router.post("/ingest/text", response_model=IngestTextOut)
def ingest_text_route(payload: IngestTextIn, db: Session = Depends(get_db)):
    try:
        doc_id = ingest_text(
            db,
            name=payload.name,
            text=payload.text,
            metadata=payload.metadata or {},
        )
        return IngestTextOut(document_id=str(doc_id))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ingerir: {type(e).__name__}: {e}")
    

@router.post("/search", response_model=RagSearchOut)
def rag_search(payload: RagSearchIn, db: Session = Depends(get_db)):
    try:
        hits = retrieve_top_k(
            db=db,
            query=payload.query,
            top_k=payload.top_k,
            filters=payload.filters,
        )

        return RagSearchOut(
            query=payload.query,
            top_k=payload.top_k,
            hits=[
                RagHitOut(
                    chunk_id=h.chunk_id,
                    document_id=h.document_id,
                    document_name=h.document_name,
                    score=h.score,
                    content=h.content,
                    metadata=h.metadata,
                )
                for h in hits
            ],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no search: {type(e).__name__}: {e}")
    

@router.post("/ingest/pdf", response_model=IngestPdfOut)
def ingest_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.content_type not in ("application/pdf", "application/x-pdf"):
        raise HTTPException(status_code=400, detail="Envie um arquivo PDF")
    
    pdf_bytes = file.file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Arquivo vazio")
    
    name = file.filename or "document.pdf"

    try:
        text = extract_text_from_pdf_bytes(pdf_bytes)
        if not text.strip():
            raise HTTPException(status_code=400, detail="Não consegui extrair o texto desse PDF")
        
        doc_id = ingest_text(
            db,
            name=name,
            text=text,
            source_type="pdf",
            source_uri=name,
            mime_type="application/pdf",
            metadata={
                "filename": name,
                "content_type": file.content_type,
                "sha256_pdf": hashlib.sha256(pdf_bytes).hexdigest(),
            },
            chunk_size=1200,
            overlap=150,
        )

        return IngestPdfOut(document_id=str(doc_id), name=name, pages_text_chars=len(text))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ingerir PDF: {type(e).__name__}: {e}")