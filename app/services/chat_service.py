import uuid
from sqlalchemy.orm import Session
from app.models import Message

def get_session_history(db: Session, session_id, limit: int = 20):
    msgs = (
        db.query(Message)
        .filter(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
        .all()
    )
    msgs.reverse()

    return msgs

def save_user_and_assistant_messages(db: Session, session_id, user_text: str, assistant_text: str):
    user_msg = Message(
        id=uuid.uuid4(),
        session_id=session_id,
        role="user",
        content=user_text
    )

    assistant_msg = Message(
        id=uuid.uuid4(),
        session_id=session_id,
        role="assistant",
        content=assistant_text
    )

    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()
    db.refresh(user_msg)
    db.refresh(assistant_msg)

    return user_msg, assistant_msg