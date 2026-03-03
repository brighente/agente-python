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

    r = requests.post(
        f"{API_BASE}/chat/send",
        json={
            "user_id": st.session_state.user["id"],
            "session_id": st.session_state.session["id"],
            "message": msg,
        },
    )
    r.raise_for_status()
    reply = r.json()["reply"]

    with st.chat_message("assistant"):
        st.markdown(reply)

    st.rerun()