from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db import get_db
from app.api.routes_chat import router as chat_router

app = FastAPI(title="Agente Python (FastAPI + Agno)")

@app.get("/")
def healthCheck():
    return {"status": "ok", "message": "API rodando"}

app.include_router(chat_router)