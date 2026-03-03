from sqlalchemy.orm import Session
from app.agent.agno_agent import build_agent
from app.agent.tools import count_messages_in_session, list_user_sessions, get_recent_messages

def build_prompt(system_msg: str, historico: str, user_message: str) -> str:
    return(
        f"SYSTEM: {system_msg}\n\n"
        f"HISTÓRICO (use apenas se for relevante para a pergunta atual):\n"
        f"{historico}\n\n"
        f"MENSAGEM_ATUAL (responda APENAS isso):\n"
        f"{user_message}\n\n"
        "INSTRUÇÕES IMPORTANTES:\n"
        "- Ignore assuntos anteriores que não sejam relevantes.\n"
        "- Não repita respostas anteriores.\n"
        "- Só use ferramentas se forem necessárias para responder a MENSAGEM_ATUAL.\n"
    )

def make_tools(db: Session, user_id: str, session_id: str, tools_used: list[str]):
    def tool_get_recent_messages(limit: int = 10) -> str:
        tools_used.append(f"tool_get_recent_messages(limit={limit})")
        print(f"[TOOL] tool_get_recent_messages(limit={limit})")
        return get_recent_messages(db, session_id, limit=limit)
    
    def tool_count_messages() -> int:
        tools_used.append(f"tool_count_messages()")
        print(f"[TOOL] tool_count_messages()")
        return count_messages_in_session(db, session_id)
    
    def tool_list_user_sessions(limit: int = 10) -> str:
        tools_used.append(f"tool_list_user_sessions(limit={limit})")
        print(f"[TOOL] tool_list_user_sessions(limit={limit})")
        return list_user_sessions(db, user_id, limit=limit)
    
    return [tool_count_messages, tool_get_recent_messages, tool_list_user_sessions]


def run_agent(db: Session, user_id: str, session_id: str, prompt: str):
    tools_used: list[str] = []
    tools = make_tools(db, user_id, session_id, tools_used)
    agent = build_agent(tools=tools)

    try:
        run = agent.run(
            input=prompt,
            user_id=user_id,
            session_id=session_id
        )
    except Exception as e:
        print(f"[AGENT ERROR] {type(e).__name__}: {e}")
        return "", tools_used

    reply = getattr(run, "content", "") or ""
    return reply, tools_used


def stream_agent(db: Session, user_id: str, session_id: str, prompt: str):
    tools_used: list[str] = []
    tools = make_tools(db, user_id, session_id, tools_used)
    agent = build_agent(tools=tools)

    try:
        stream = agent.run(
            input=prompt,
            user_id=user_id,
            session_id=session_id,
            stream=True
        )

        for event in stream:
            chunk = getattr(event, "content", None) or getattr(event, "delta", None)
            if chunk:
                yield("chunk", chunk)
        
        yield("tools", tools_used)
        yield("done", "")
        return
    except TypeError:
        pass

    except Exception as e:
        print(f"[AGENT STREAM ERROR {type(e).__name__}: {e}")
        yield("error", "Houve um erro ao se comunicar com o agente")
        yield("tools", tools_used)
        yield("done", "")
        return
        
    reply, tools_used2 = run_agent(db, user_id, session_id, prompt)
    tools_used[:] = tools_used2

    if not reply.strip():
        yield("error", "Houve um erro ao se comunicar com o agente")
        yield("tools", tools_used)
        yield("done", "")
        return
    
    for part in reply.split(" "):
        yield("chunk", part + " ")
    yield("tools", tools_used)
    yield("done", "")