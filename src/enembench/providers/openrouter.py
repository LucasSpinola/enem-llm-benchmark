"""Provedor OpenRouter, que expõe modelos variados, alguns gratuitos e alguns multimodais.

Compatível com a API da OpenAI. Os cabeçalhos de atribuição são opcionais, mas recomendados pelo
OpenRouter para identificar a aplicação.
"""

from enembench.providers.base import registrar
from enembench.providers.openai_compat import ProvedorOpenAICompat


@registrar("openrouter")
class OpenRouterProvider(ProvedorOpenAICompat):
    """Adaptador do OpenRouter. Lê a chave de OPENROUTER_API_KEY."""

    base_url = "https://openrouter.ai/api/v1"
    chave_env = "OPENROUTER_API_KEY"
    cabecalhos_extra = {
        "HTTP-Referer": "https://github.com/LucasSpinola/enem-llm-benchmark",
        "X-Title": "enem-llm-benchmark",
    }
