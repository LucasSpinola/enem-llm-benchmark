"""Interface única dos provedores de LLM e um registro simples de nome para classe.

Todo provedor recebe um prompt e imagens opcionais e devolve o texto da resposta. O núcleo conhece
apenas o `Protocol`, então adicionar um provedor novo é escrever um adaptador e registrá-lo, sem
tocar no runner. O runner monta os provedores a partir do `config/models.yaml` por `criar_provedor`.
"""

from collections.abc import Callable
from typing import Protocol, runtime_checkable


@runtime_checkable
class Provider(Protocol):
    """Contrato mínimo de um provedor: transformar um prompt em texto de resposta."""

    def responder(self, prompt: str, imagens: list[bytes] | None = None) -> str:
        """Envia o prompt ao modelo e devolve o texto da resposta."""
        ...


_REGISTRO: dict[str, Callable[..., Provider]] = {}


def registrar(nome: str) -> Callable[[Callable[..., Provider]], Callable[..., Provider]]:
    """Decorador que registra a classe de um provedor sob um nome, usado no `models.yaml`."""

    def decorador(classe: Callable[..., Provider]) -> Callable[..., Provider]:
        _REGISTRO[nome] = classe
        return classe

    return decorador


def criar_provedor(provedor: str, modelo: str, **opcoes: object) -> Provider:
    """Cria um provedor pelo nome registrado, passando o modelo e opções ao construtor."""
    if provedor not in _REGISTRO:
        conhecidos = ", ".join(sorted(_REGISTRO)) or "nenhum"
        raise ValueError(f"Provedor desconhecido: {provedor!r}. Registrados: {conhecidos}.")
    return _REGISTRO[provedor](modelo, **opcoes)
