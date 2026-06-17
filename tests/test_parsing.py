"""Testes da extração da alternativa, com respostas variadas e confusas."""

import pytest

from enembench.parsing import extrair_alternativa


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("Resposta: C", "C"),
        ("resposta - d", "D"),
        ("Alternativa C", "C"),
        ("A alternativa correta é a letra D.", "D"),
        ("Gabarito: E", "E"),
        ("Letra B", "B"),
        ("Opção A", "A"),
        ("opção: e", "E"),
        ("C", "C"),
        ("Acho que é a B.", "B"),
        # Explica antes e conclui no fim, fica com a última letra.
        ("Vejo que A está errada, B também, então a resposta é C.", "C"),
        # Conclusão explícita prevalece sobre letras citadas antes.
        (
            "A está incorreta, D parece certa, mas no fim Resposta: B",
            "B",
        ),
    ],
)
def test_extrair_alternativa(texto: str, esperado: str) -> None:
    assert extrair_alternativa(texto) == esperado


@pytest.mark.parametrize(
    "texto",
    [
        "",
        "   ",
        "Não sei responder a essa questão.",
        "Faltou informação no enunciado.",
    ],
)
def test_extrair_alternativa_sem_letra(texto: str) -> None:
    assert extrair_alternativa(texto) is None


def test_extrair_alternativa_normaliza_maiuscula() -> None:
    assert extrair_alternativa("resposta: c") == "C"


def test_extrair_alternativa_ignora_letras_fora_de_ae() -> None:
    # F, G, Z não são alternativas; só conta A a E.
    assert extrair_alternativa("Entre as opções F e G, escolho a resposta D.") == "D"
