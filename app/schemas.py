from typing import Any, List

from pydantic import BaseModel, EmailStr
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