"""Adaptador base para provedores compatíveis com a API da OpenAI, como Groq e OpenRouter.

Os dois falam o mesmo protocolo de chat da OpenAI, mudando só a URL base, a chave e alguns
cabeçalhos. Este adaptador concentra a lógica comum, inclusive o envio de imagem como data URL em
base64, e o SDK trata os erros transitórios com retry e backoff. As subclasses só declaram a URL, a
variável de ambiente da chave e os cabeçalhos extras.
"""

import base64
import os

_MAX_TENTATIVAS = 4
_MIME_PADRAO = "image/png"


class ProvedorOpenAICompat:
    """Base para provedores que usam o SDK da OpenAI apontando para outro endpoint."""

    base_url: str = ""
    chave_env: str = ""
    cabecalhos_extra: dict[str, str] = {}

    def __init__(self, modelo: str) -> None:
        from openai import OpenAI

        chave = os.environ.get(self.chave_env)
        if not chave:
            raise RuntimeError(
                f"Variável de ambiente {self.chave_env} não configurada. Defina-a no arquivo .env."
            )
        self.modelo = modelo
        self._cliente = OpenAI(api_key=chave, base_url=self.base_url, max_retries=_MAX_TENTATIVAS)

    def _conteudo(self, prompt: str, imagens: list[bytes] | None) -> object:
        """Monta o conteúdo da mensagem: texto puro, ou texto mais imagens quando houver."""
        if not imagens:
            return prompt
        partes: list[dict] = [{"type": "text", "text": prompt}]
        for imagem in imagens:
            dados = base64.standard_b64encode(imagem).decode("ascii")
            partes.append(
                {"type": "image_url", "image_url": {"url": f"data:{_MIME_PADRAO};base64,{dados}"}}
            )
        return partes

    def responder(self, prompt: str, imagens: list[bytes] | None = None) -> str:
        """Envia o prompt e as imagens ao modelo e devolve o texto da resposta."""
        resposta = self._cliente.chat.completions.create(
            model=self.modelo,
            messages=[{"role": "user", "content": self._conteudo(prompt, imagens)}],
            extra_headers=self.cabecalhos_extra or None,
        )
        return resposta.choices[0].message.content or ""
