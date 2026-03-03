from agno.agent import Agent
from agno.models.openai import OpenAIChat
from app.config import settings

BASE_INSTRUCTIONS = [
        "Você é um assistente virtual que fala sobre futebol em geral, mas especialmente sobre futebol brasileiro",
        "Seu carro chefe é falar sobre estatísticas, campeões, jogadores e afins",
        "Seja levemente engraçado, e utilize gírias e linguajar de boleiro",
        "Utilize poucos ou nenhum emoji"
    ]

def build_agent(tools: list) -> Agent:
    return Agent(
    name="Agente Python de Estudos",
    model=OpenAIChat(id=settings.openai_model, api_key=settings.openai_api_key),
    instructions=BASE_INSTRUCTIONS,
    tools=tools,
    markdown=True
)