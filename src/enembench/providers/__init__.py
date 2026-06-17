"""Adaptadores de provedores de LLM, cada um atrás da mesma interface.

Importar os adaptadores concretos aqui faz o decorador `registrar` rodar, então o registro fica
pronto e `criar_provedor` consegue montar qualquer provedor pelo nome do `models.yaml`. Os SDKs só
carregam quando o provedor é instanciado, então este import não exige as bibliotecas nem as chaves.
"""

from enembench.providers.base import Provider, criar_provedor, registrar
from enembench.providers.fake import FakeProvider
from enembench.providers.gemini import GeminiProvider
from enembench.providers.groq import GroqProvider
from enembench.providers.openrouter import OpenRouterProvider

__all__ = [
    "FakeProvider",
    "GeminiProvider",
    "GroqProvider",
    "OpenRouterProvider",
    "Provider",
    "criar_provedor",
    "registrar",
]
