import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User, Message, ChatSession
from app.agent.agno_agent import build_agent
from app.agent.tools import get_recent_messages, count_messages_in_session, list_user_sessions
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

    # 2- Buscar historico de conversa
    historico = (
        db.query(Message).filter(Message.session_id == payload.session_id).order_by(Message.created_at.desc()).limit(20).all()
    )

    historico.reverse() # volta a ordem

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

    historico_formatado = "\n".join(historico_formatado)

    prompt = (
        f"SYSTEM: {system_msg}\n\n"
        f"HISTÓRICO (use apenas se for relevante para a pergunta atual):\n"
        f"{historico_formatado}\n\n"
        f"MENSAGEM_ATUAL (responda APENAS isso):\n"
        f"{payload.message}\n\n"
        "INSTRUÇÕES IMPORTANTES:\n"
        "- Ignore assuntos anteriores que não sejam relevantes.\n"
        "- Não repita respostas anteriores.\n"
        "- Só use ferramentas se forem necessárias para responder a MENSAGEM_ATUAL.\n"
    )

    # 4- Define as tools do agente
    def tool_get_recent_messages(limit: int = 10) -> str:
        print(f"[TOOL] tool_get_recent_messages(limit={limit})") 
        return get_recent_messages(db, str(payload.session_id), limit=limit)
    
    
    def tool_count_messages() -> int:
        print(f"[TOOL] tool_count_messages()")
        return count_messages_in_session(db, str(payload.session_id))
    
    def tool_list_user_sessions(limit: int = 10) -> str:
        print(f"[TOOL] tool_list_user_sessions(limit={limit})")
        return list_user_sessions(db, str(payload.user_id), limit=limit)

    agent = build_agent(tools=[tool_count_messages, tool_get_recent_messages, tool_list_user_sessions])

    # 5- Inicia o agente
    try:
        run = agent.run(
            input=prompt,
            user_id=str(payload.user_id),
            session_id=str(payload.session_id),
        )

    except Exception as e:
        print(f"[AGENT ERROR] {type(e).__name__}: {e}")
        return SendMessageOut(reply="Houve um erro ao se comunicar com o agente")

    reply = run.content if run and run.content else ""

    if reply == "":
        return SendMessageOut(reply="Houve um erro ao se comunicar com o agente")
        
    # 6- Salva mensagem do usuário
    user_msg = Message(
        id=uuid.uuid4(),
        session_id=payload.session_id,
        role="user",
        content=payload.message
    )

    # 7- Salva mensagem do assistente
    assistant_msg = Message(
        id=uuid.uuid4(),
        session_id=payload.session_id,
        role="assistant",
        content=reply
    )

    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()
    db.refresh(user_msg)
    db.refresh(assistant_msg)

    return SendMessageOut(reply=reply)