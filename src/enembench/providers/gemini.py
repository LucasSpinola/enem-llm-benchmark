"""Provedor real do Google Gemini, via SDK google-genai, com suporte a imagem.

Lê a chave do ambiente em tempo de execução, falha com mensagem clara se ela não estiver definida,
e trata erros transitórios do free tier com retry e backoff exponencial. O SDK é importado de forma
tardia, então só carregar o módulo não exige a biblioteca nem a chave.
"""

import logging
import os
import time

from enembench.providers.base import registrar

logger = logging.getLogger(__name__)

_MAX_TENTATIVAS = 4
_BACKOFF_BASE_S = 2.0
# Códigos HTTP que valem nova tentativa: limite de taxa e erros temporários do servidor.
_CODIGOS_TRANSITORIOS = {429, 500, 502, 503, 504}
_MIME_PADRAO = "image/png"


@registrar("gemini")
class GeminiProvider:
    """Adaptador do Gemini. Recebe o id do modelo, ex: 'gemini-2.0-flash'."""

    def __init__(self, modelo: str, *, chave_env: str = "GEMINI_API_KEY") -> None:
        from google import genai  # import tardio, só quando o provedor é realmente usado

        chave = os.environ.get(chave_env)
        if not chave:
            raise RuntimeError(
                f"Variável de ambiente {chave_env} não configurada. Defina-a no arquivo .env."
            )
        self.modelo = modelo
        self._cliente = genai.Client(api_key=chave)

    def responder(self, prompt: str, imagens: list[bytes] | None = None) -> str:
        """Envia o prompt e as imagens ao Gemini e devolve o texto da resposta."""
        from google.genai import types

        conteudo: list[object] = [prompt]
        for imagem in imagens or []:
            conteudo.append(types.Part.from_bytes(data=imagem, mime_type=_MIME_PADRAO))
        resposta = self._gerar_com_retentativa(conteudo)
        return resposta.text or ""

    def _gerar_com_retentativa(self, conteudo: list[object]) -> object:
        """Chama o modelo, tentando de novo com backoff em erros transitórios do free tier."""
        from google.genai import errors

        for tentativa in range(_MAX_TENTATIVAS):
            try:
                return self._cliente.models.generate_content(model=self.modelo, contents=conteudo)
            except errors.APIError as erro:
                ultima = tentativa == _MAX_TENTATIVAS - 1
                if erro.code not in _CODIGOS_TRANSITORIOS or ultima:
                    raise
                espera = _BACKOFF_BASE_S * (2**tentativa)
                logger.warning(
                    "Gemini devolveu erro %s, nova tentativa em %.1fs", erro.code, espera
                )
                time.sleep(espera)
        raise RuntimeError("Falha ao chamar o Gemini após várias tentativas")  # pragma: no cover
