from agno.agent import Agent
from agno.models.openai import OpenAIChat
from app.config import settings

agent = Agent(
    name="Agente Python de Estudos",
    model=OpenAIChat(id=settings.openai_model, api_key=settings.openai_api_key),
    instructions=[
        "Você é um assistente virtual que fala sobre futebol em geral, mas especialmente sobre futebol brasileiro",
        "Seu carro chefe é falar sobre estatísticas, campeões, jogadores e afins",
        "Seja levemente engraçado, usando gírias e palavras do vocabulário de futebol"
    ],
    markdown=True
)