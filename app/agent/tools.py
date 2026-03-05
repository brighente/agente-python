from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import Message, ChatSession
from app.rag.retriever_service import retrieve_top_k

def get_recent_messages(db: Session, session_id: str, limit: int = 10) -> str:
    # Traz as últimas 10 mensagens da sessão (5 interacoes user -> Agente)

    msgs = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )
    msgs.reverse()

    lines = []
    for m in msgs:
        lines.append(f"{m.role}: {m.content}")

    return "\n".join(lines) if lines else "(Sem histórico de mensagens recente)"


def count_messages_in_session(db: Session, session_id: str) -> int:
    # Faz a contagem no banco de quantas mensagens tem nessa sessao

    return(
        db.query(func.count(Message.id))
        .filter(Message.session_id == session_id)
        .scalar()
        or 0
    )


def list_user_sessions(db: Session, user_id: str, limit: int = 10) -> str:
    # Traz as últimas 10 sessões de chat do usuário

    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user_id)
        .order_by(ChatSession.created_at.desc())
        .limit(limit)
        .all()
    )

    if not sessions:
        return "(nenhuma sessão encontrada)"

    lines = []
    for l in sessions:
        lines.append(f"{l.id} | {l.title or '(Sem Título)'}")

    return "\n".join(lines)


def retrieve_context(db: Session, query: str, top_k: int = 5) -> str:
    hits = retrieve_top_k(db=db, query=query, top_k=top_k)

    if not hits:
        return "(Nenhum contexto relevante encontrado na base.)"
    
    lines = []
    for i, h in enumerate(hits, start=1):
        src = h.document_name or h.document_id
        lines.append(f"[{i}] fonte: {src} | score: {h.score:.3f}\n{h.content}")

    return "\n\n".join(lines)