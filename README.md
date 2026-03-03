# 🤖 Agente de IA com Python (Projeto de Estudos)

Este é um projeto pessoal de estudos onde estou desenvolvendo um **Agente de IA em Python** utilizando arquitetura moderna de backend, streaming de respostas e integração com banco de dados.

O principal objetivo deste projeto é:

- Aprender e aprofundar conhecimentos em **Python**
- Aprimorar conhecimentos no desenvolvimento de **Agentes de IA**
- Estudar boas práticas de **arquitetura backend**
- Trabalhar com **ORM, banco de dados e streaming**

---

# 🧠 O que o projeto faz atualmente

- ✅ Criação de usuários
- ✅ Criação de sessões de chat
- ✅ Persistência de mensagens em PostgreSQL
- ✅ Agente de IA usando **Agno**
- ✅ Uso de **Tools (ferramentas)** controladas pelo agente
- ✅ Streaming de resposta
- ✅ Exibição das ferramentas utilizadas em cada resposta
- ✅ Separação em camadas (Rotas → Services → Agent → Tools)

---

# 🏗️ Arquitetura

O projeto foi estruturado em camadas:

```
app/
│
├── api/
│ └── routes_chat.py # Camada HTTP (FastAPI)
│
├── services/
│ ├── chat_service.py # Lógica de persistência
│ └── agent_service.py # Execução do agente e streaming
│
├── agent/
│ ├── agno_agent.py # Construção do agente
│ └── tools.py # Ferramentas do agente
│
├── models.py # ORM (SQLAlchemy)
├── schemas.py # Schemas Pydantic
├── db.py # Configuração do banco
├── config.py # Variáveis de ambiente
```

### 🔄 Fluxo de execução

1. Frontend (Streamlit) envia mensagem
2. FastAPI recebe e valida
3. Service monta prompt
4. Agent decide se usa tools
5. Streaming retorna chunks da resposta
6. Mensagens são persistidas no banco

---

# 🛠️ Tecnologias Utilizadas

- **Python 3.12+**
- **FastAPI**
- **SQLAlchemy (ORM)**
- **PostgreSQL**
- **Agno (Framework de Agentes)**
- **OpenAI Chat Model**
- **Streamlit (Frontend)**
- **Server-Sent Events (Streaming)**
