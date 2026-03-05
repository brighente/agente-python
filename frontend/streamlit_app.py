import json

import requests
import streamlit as st

API_BASE = "http://127.0.0.1:8000"

st.set_page_config(page_title="Agente IA", page_icon="🤖")
st.title("🤖 Chat com Agente (Agno + FastAPI)")

if "user" not in st.session_state:
    st.session_state.user = None
if "session" not in st.session_state:
    st.session_state.session = None

with st.sidebar:
    st.subheader("Identificação")

    name = st.text_input("Nome", value="João")
    email = st.text_input("Email", value="joao@teste.com")
    title = st.text_input("Título da sessão", value="Minha sessão")

    if st.button("Criar/Obter Usuário"):
        r = requests.post(f"{API_BASE}/chat/users", json={"name": name, "email": email})
        r.raise_for_status()
        st.session_state.user = r.json()
        st.success("Usuário pronto!")

    if st.session_state.user and st.button("Criar Sessão"):
        r = requests.post(
            f"{API_BASE}/chat/sessions",
            json={"user_id": st.session_state.user["id"], "title": title},
        )
        r.raise_for_status()
        st.session_state.session = r.json()
        st.success("Sessão criada!")

    st.divider()
    st.subheader("📚 RAG (Base de Conhecimento)")

    uploaded = st.file_uploader("Enviar PDF para o RAG", type=["pdf"])
    if uploaded and st.button("Ingerir PDF"):
        files = {"file": (uploaded.name, uploaded.getvalue(), "application/pdf")}
        r = requests.post(f"{API_BASE}/rag/ingest/pdf", files=files)
        if r.status_code != 200:
            st.error(f"Erro: {r.text}")
        else:
            data = r.json()
            st.success(f"Ingerido! document_id={data['document_id']}")
            st.caption(f"Texto extraído (chars): {data['pages_text_chars']}")
    st.divider()
    st.subheader("🔎 Debug Search")

    search_q = st.text_input("Buscar na base (pgvector)", value="")
    top_k = st.slider("Top K", min_value=1, max_value=20, value=5)

    if st.button("Buscar") and search_q.strip():
        r = requests.post(f"{API_BASE}/rag/search", json={"query": search_q, "top_k": top_k})
        if r.status_code != 200:
            st.error(f"Erro: {r.text}")
        else:
            res = r.json()
            hits = res.get("hits", [])
            st.write(f"Resultados: {len(hits)}")
            for i, h in enumerate(hits, start=1):
                st.markdown(f"**[{i}] {h['document_name']} — score {h['score']:.3f}**")
                st.code(h["content"][:1200])

st.divider()

if not st.session_state.user or not st.session_state.session:
    st.info("Crie/obtenha usuário e depois crie uma sessão no menu lateral.")
    st.stop()

# Carregar histórico
hist = requests.get(
    f"{API_BASE}/chat/sessions/{st.session_state.session['id']}/messages"
).json()

for m in hist:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

msg = st.chat_input("Digite sua mensagem...")
if msg:
    with st.chat_message("user"):
        st.markdown(msg)

    assistant_box = st.chat_message("assistant")
    text_slot = assistant_box.empty()
    tools_slot = assistant_box.empty()

    full_text = ""
    tools_used = []

    with requests.post(
        f"{API_BASE}/chat/send/stream",
        json={
            "user_id": st.session_state.user["id"],
            "session_id": st.session_state.session["id"],
            "message": msg,
        },
        stream=True,
    ) as r:
        r.raise_for_status()

        event_type = None
        for raw in r.iter_lines(decode_unicode=True):
            if not raw:
                continue

            if raw.startswith("event:"):
                event_type = raw.replace("event:", "").strip()
                continue

            if raw.startswith("data:"):
                payload_json = raw.replace("data:", "").strip()
                data = json.loads(payload_json)

                if event_type == "chunk":
                    full_text += data["text"]
                    text_slot.markdown(full_text)

                elif event_type == "tools":
                    tools_used = data.get("tools_used", [])
                    if tools_used:
                        tools_slot.caption("🛠️ Tools: " + ", ".join(tools_used))

                elif event_type == "error":
                    text_slot.error(data.get("message", "Erro"))
                    break

                elif event_type == "done":
                    if not data.get("ok", True) and not full_text:
                        text_slot.error("Erro: resposta vazia do agente")
                    final_tools = data.get("tools_used", tools_used)
                    if final_tools:
                        tools_slot.caption("🛠️ Tools: " + ", ".join(final_tools))
                    break

    st.rerun()