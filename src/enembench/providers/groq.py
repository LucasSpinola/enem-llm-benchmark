"""Provedor Groq, inferência rápida e gratuita de modelos abertos, no protocolo da OpenAI."""

from enembench.providers.base import registrar
from enembench.providers.openai_compat import ProvedorOpenAICompat


@registrar("groq")
class GroqProvider(ProvedorOpenAICompat):
    """Adaptador do Groq. Lê a chave de GROQ_API_KEY."""

    base_url = "https://api.groq.com/openai/v1"
    chave_env = "GROQ_API_KEY"
