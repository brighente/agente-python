from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models import Message, ChatSession

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
        lines.append(f"{l.id} | {l.title or "(Sem Título)"}")

    return "\n".join(lines)