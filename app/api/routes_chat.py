import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User, Message, ChatSession
from app.schemas import (
    UserUpsertIn, UserOut,
    ChatSessionCreateIn, ChatSessionOut,
    MessageCreateIn, MessageOut
)

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/users", response_model=UserOut)
def upsert_user(payload: UserUpsertIn, db: Session = Depends(get_db)):
    # Cria usuário se não existir, senão retorna o que já existe #

    user = db.query(User).filter(User.email == payload.email).one_or_none()
    if user:
        return user
    
    user = User(
        id=uuid.uuid4(),
        name=payload.name,
        email=payload.email
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/sessions", response_model=ChatSessionOut)
def create_session(payload: ChatSessionCreateIn, db: Session = Depends(get_db)):
    # Cria sessao de chata associada a um user_id #
    
    user = db.query(User).filter(User.id == payload.user_id).one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    if payload.title == "":
        payload.title = "Nova Conversa"
    
    sess = ChatSession(
        id=uuid.uuid4(),
        user_id=payload.user_id,
        title=payload.title
    )

    db.add(sess)
    db.commit()
    db.refresh(sess)
    return sess


@router.post("/messages", response_model=MessageOut)
def add_message(payload: MessageCreateIn, db: Session = Depends(get_db)):
    # Salva uma mensagem na sessão #

    sess = db.query(ChatSession).filter(ChatSession.id == payload.session_id).one_or_none()
    if not sess:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")

    msg = Message(
        id=uuid.uuid4(),
        session_id=payload.session_id,
        role=payload.role,
        content=payload.content
    ) 
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


@router.get("/sessions/{session_id}/messages", response_model=list[MessageOut])
def list_messages(session_id: str, db: Session = Depends(get_db)):
    # Lista mensagens da sessão, em ordem #

    try:
        sid=uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="session_id inválido")
    
    msgs=(
        db.query(Message)
        .filter(Message.session_id == sid)
        .order_by(Message.created_at.asc())
        .all()
    )
    return msgs