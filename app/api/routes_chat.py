import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User, Message, ChatSession
from app.agent.agno_agent import agent
from app.schemas import (
    UserUpsertIn, UserOut,
    ChatSessionCreateIn, ChatSessionOut,
    MessageCreateIn, MessageOut,
    SendMessageIn, SendMessageOut
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


@router.post("/send/", response_model=SendMessageOut)
def send(payload: SendMessageIn, db: Session = Depends(get_db)):
    # 1- Validacao da sessao do usuario
    user = db.query(User).filter(User.id == payload.user_id).one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    sess = db.query(ChatSession).filter(ChatSession.id == payload.session_id).one_or_none()
    if not sess:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")

    # 2- Salvar mensagem no banco
    user_msg = Message(
        id=uuid.uuid4(),
        session_id=payload.session_id,
        role="user",
        content=payload.message
    )
    db.add(user_msg)
    db.commit()

    # 3- Buscar historico de conversa
    historico = (
        db.query(Message).filter(Message.session_id == payload.session_id).order_by(Message.created_at.desc()).limit(20).all()
    )

    historico.reverse() # volta a ordem

    # 4- Monta o contexto
    system_msg=(
        "Você está conversando em um chat."
        "Use o histórico apenas como contexto para conversa."
        "Responda sempre em português."
    )

    historico_formatado = []
    for m in historico:
        role = m.role.lower().strip()
        if role not in ("user", "assistant", "system"):
            role = "user"

        historico_formatado.append(f"{role}: {m.content}")

    historico_formatado = "\n".join(historico_formatado)

    prompt = (
        f"SYSTEM: {system_msg}\n\n"
        f"HISTÓRICO: (role: conteúdo):\n{historico_formatado}\n\n"
        f"Agora responda a última mensagem do usuário de forma útil e objetiva."
    )

    # 5- Inicia o agente
    run = agent.run(
        input=prompt,
        user_id=str(payload.user_id),
        session_id=str(payload.session_id),
    )

    reply = run.content if run and run.content else ""

    # 6 - Salva mensagem do assistente
    assistant_msg = Message(
        id=uuid.uuid4(),
        session_id=payload.session_id,
        role="assistant",
        content=reply
    )
    db.add(assistant_msg)
    db.commit()
    db.refresh(assistant_msg)

    return SendMessageOut(reply=reply)