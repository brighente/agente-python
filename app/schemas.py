from typing import Any, List

from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from datetime import datetime

class UserUpsertIn(BaseModel):
    name: str
    email: EmailStr


class UserOut(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    created_at: datetime


class ChatSessionCreateIn(BaseModel):
    user_id: UUID
    title: str | None = None


class ChatSessionOut(BaseModel):
    id: UUID
    user_id: UUID
    title: str | None
    created_at: datetime


class MessageCreateIn(BaseModel):
    session_id: UUID
    role: str #user | assistant | system
    content: str


class MessageOut(BaseModel):
    id: UUID
    session_id: UUID
    role: str
    content: str
    created_at: datetime


class SendMessageIn(BaseModel):
    user_id: UUID
    session_id: UUID
    message: str


class SendMessageOut(BaseModel):
    reply: str
    tools_used: List[str] = []


class IngestTextIn(BaseModel):
    name: str
    text: str
    metadata: dict[str, Any] | None = None


class IngestTextOut(BaseModel):
    document_id: str


class RagSearchIn(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    filters: dict[str, Any] | None = None


class RagHitOut(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    score: float
    content: str
    metadata: dict[str, Any]


class RagSearchOut(BaseModel):
    query: str
    top_k: int
    hits: list[RagHitOut]


class IngestPdfOut(BaseModel):
    document_id: str
    name: str
    pages_text_chars: int