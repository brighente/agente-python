from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db import get_db

app = FastAPI(title="Agente Python (FastAPI + Agno)")

@app.get("/")
def healthCheck():
    return {"status": "ok", "message": "API rodando"}


@app.get("/db-test")
def test_db(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT 1"))
    return {"db_response": result.scalar()}
