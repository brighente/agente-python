from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import IngestTextIn, IngestTextOut
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