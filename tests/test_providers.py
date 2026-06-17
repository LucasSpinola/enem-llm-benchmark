"""Testes do registro de provedores e do fluxo questão para letra com o FakeProvider, sem rede."""

import pytest

from enembench.parsing import extrair_alternativa
from enembench.prompt import montar_prompt
from enembench.providers import FakeProvider, criar_provedor
from enembench.providers.base import Provider
from enembench.schema import Questao


def _questao() -> Questao:
    return Questao(
        id="enem-2025-07",
        ano=2025,
        area="linguagens",
        enunciado="Qual é o tema central do texto?",
        alternativas={"A": "um", "B": "dois", "C": "tres", "D": "quatro", "E": "cinco"},
        gabarito="C",
        tem_imagem=False,
        imagens=[],
    )


def test_criar_provedor_fake() -> None:
    provedor = criar_provedor("fake", "fake")
    assert isinstance(provedor, Provider)


def test_criar_provedor_desconhecido() -> None:
    with pytest.raises(ValueError):
        criar_provedor("inexistente", "qualquer")


@pytest.mark.parametrize(
    ("provedor", "chave_env", "modelo"),
    [
        ("groq", "GROQ_API_KEY", "llama-3.1-8b-instant"),
        ("openrouter", "OPENROUTER_API_KEY", "meta-llama/llama-3.3-70b-instruct:free"),
    ],
)
def test_provedor_openai_compat_exige_chave(
    provedor: str, chave_env: str, modelo: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(chave_env, raising=False)
    with pytest.raises(RuntimeError):
        criar_provedor(provedor, modelo)


@pytest.mark.parametrize(
    ("provedor", "chave_env", "modelo"),
    [
        ("groq", "GROQ_API_KEY", "llama-3.1-8b-instant"),
        ("openrouter", "OPENROUTER_API_KEY", "meta-llama/llama-3.3-70b-instruct:free"),
    ],
)
def test_provedor_openai_compat_constroi_com_chave(
    provedor: str, chave_env: str, modelo: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(chave_env, "chave-de-teste")
    assert isinstance(criar_provedor(provedor, modelo), Provider)


def test_fake_provider_devolve_resposta_fixa_e_registra_chamada() -> None:
    provedor = FakeProvider(resposta="Resposta: C")
    saida = provedor.responder("um prompt", imagens=[b"abc"])
    assert saida == "Resposta: C"
    assert len(provedor.chamadas) == 1
    assert provedor.chamadas[0].prompt == "um prompt"
    assert provedor.chamadas[0].imagens == [b"abc"]


def test_fluxo_questao_para_letra() -> None:
    # Uma questão vira prompt, o provedor responde, e a letra é extraída.
    questao = _questao()
    provedor = FakeProvider(resposta="Penso que o tema é o trabalho. Resposta: C")

    prompt = montar_prompt(questao)
    resposta_crua = provedor.responder(prompt)
    alternativa = extrair_alternativa(resposta_crua)

    assert alternativa == "C"
    assert alternativa == questao.gabarito  # acertou
    assert questao.enunciado in provedor.chamadas[0].prompt
