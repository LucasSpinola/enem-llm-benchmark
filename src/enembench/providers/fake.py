"""Provedor falso, para testar prompt, runner e cache sem tocar em nenhuma rede.

Devolve uma resposta fixa e guarda as chamadas que recebeu, para os testes conferirem o que foi
enviado, inclusive se as imagens chegaram.
"""

from dataclasses import dataclass

from enembench.providers.base import registrar


@dataclass(frozen=True)
class _Chamada:
    """Registro de uma chamada recebida pelo provedor falso."""

    prompt: str
    imagens: list[bytes]


@registrar("fake")
class FakeProvider:
    """Provedor sem rede que sempre devolve a mesma resposta e registra as chamadas."""

    def __init__(self, modelo: str = "fake", resposta: str = "Resposta: A") -> None:
        self.modelo = modelo
        self.resposta = resposta
        self.chamadas: list[_Chamada] = []

    def responder(self, prompt: str, imagens: list[bytes] | None = None) -> str:
        """Registra a chamada e devolve a resposta fixa."""
        self.chamadas.append(_Chamada(prompt=prompt, imagens=list(imagens or [])))
        return self.resposta
