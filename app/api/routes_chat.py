import json
import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User, Message, ChatSession
from app.schemas import (
    UserUpsertIn, UserOut,
    ChatSessionCreateIn, ChatSessionOut,
    MessageCreateIn, MessageOut,
    SendMessageIn, SendMessageOut
)
from app.services.agent_service import build_prompt, run_agent, stream_agent
from app.services.chat_service import get_session_history, save_user_and_assistant_messages

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


@router.post("/send", response_model=SendMessageOut)
def send(payload: SendMessageIn, db: Session = Depends(get_db)):
    # 1- Validacao da sessao do usuario
    user = db.query(User).filter(User.id == payload.user_id).one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    sess = db.query(ChatSession).filter(ChatSession.id == payload.session_id).one_or_none()
    if not sess:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")

    # 2- Buscar historico de conversa
    historico = get_session_history(db, payload.session_id, limit=20)

    # 3- Monta o contexto
    system_msg=(
        "Você está conversando em um chat. "
        "Use o histórico apenas como contexto para conversa. "
        "Responda sempre em português. "
    )

    historico_formatado = []
    for m in historico:
        role = m.role.lower().strip()
        if role not in ("user", "assistant", "system"):
            role = "user"

        historico_formatado.append(f"{role}: {m.content}")

    historico_formatado = "\n".join(historico_formatado) or "(Sem Histórico)"

    prompt = build_prompt(system_msg, historico_formatado, payload.message)

    # 4- Define as tools do agente
    
    reply, tools_used = run_agent(db, str(payload.user_id), str(payload.session_id), prompt)

    if not reply.strip():
        return SendMessageOut(reply="Houve um erro ao se comunicar com o agente", tools_used=tools_used)
    
    save_user_and_assistant_messages(db, payload.session_id, payload.message, reply)

    return SendMessageOut(reply=reply, tools_used=tools_used)


@router.post("/send/stream")
def send_stream(payload: SendMessageIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == payload.user_id).one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    session = db.query(ChatSession).filter(ChatSession.id == payload.session_id).one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    historico = get_session_history(db, payload.session_id, limit=20)
    historico_formatado = []
    for linha in historico:
        role = linha.role.lower().strip()
        if role not in("user", "system", "assistant"):
            role = "user"

        historico_formatado.append(f"{role}: {linha.content}")
    
    historico_formatado = "\n".join(historico_formatado) or "(Sem Histórico)"

    system_msg = (
        "Você está conversando em um chat. "
        "Use o histórico apenas como contexto. "
        "Responda sempre em português."
    )

    prompt = build_prompt(system_msg, historico_formatado, payload.message)

    def event_stream():
        full_reply_parts = []
        last_tools_used = []

        for event_type, data in stream_agent(db, str(payload.user_id), str(payload.session_id), prompt):
            if event_type == "chunk":
                full_reply_parts.append(data)
                yield f"event: chunk\ndata: {json.dumps({'text': data})}\n\n"
            elif event_type == "tools":
                last_tools_used = data
                yield f"event: tools\ndata: {json.dumps({'tools_used': data})}\n\n"
            elif event_type == "error":
                yield f"event: error\ndata: {json.dumps({'message': data})}\n\n"
            elif event_type == "done":
                full_reply = "".join(full_reply_parts).strip()
                if full_reply:
                    save_user_and_assistant_messages(db, payload.session_id, payload.message, full_reply)
                yield f"event: done\ndata: {json.dumps({'ok': bool(full_reply), 'tools_used': last_tools_used})}\n\n"
                return
        
    return StreamingResponse(event_stream(), media_type="text/event-stream")
