"""Testes dos helpers puros de normalização, compartilhados pelas fontes de dados."""

import pytest

from enembench.normalizacao import alternativas_para_dict, area_de_numero, contar_por_area
from enembench.schema import (
    AREA_HUMANAS,
    AREA_LINGUAGENS,
    AREA_MATEMATICA,
    AREA_NATUREZA,
    Questao,
)


@pytest.mark.parametrize(
    ("numero", "area"),
    [
        (1, AREA_LINGUAGENS),
        (45, AREA_LINGUAGENS),
        (46, AREA_HUMANAS),
        (90, AREA_HUMANAS),
        (91, AREA_NATUREZA),
        (135, AREA_NATUREZA),
        (136, AREA_MATEMATICA),
        (180, AREA_MATEMATICA),
    ],
)
def test_area_de_numero_nas_fronteiras(numero: int, area: str) -> None:
    assert area_de_numero(numero) == area


@pytest.mark.parametrize("numero", [0, -1, 181, 200])
def test_area_de_numero_fora_do_intervalo(numero: int) -> None:
    with pytest.raises(ValueError):
        area_de_numero(numero)


def test_alternativas_para_dict() -> None:
    resultado = alternativas_para_dict(["aa", "bb", "cc", "dd", "ee"])
    assert resultado == {"A": "aa", "B": "bb", "C": "cc", "D": "dd", "E": "ee"}


def test_alternativas_para_dict_quantidade_errada() -> None:
    with pytest.raises(ValueError):
        alternativas_para_dict(["aa", "bb", "cc"])


def _questao(numero: int, area: str) -> Questao:
    return Questao(
        id=f"enem-2023-{numero:02d}",
        ano=2023,
        area=area,
        enunciado="q",
        alternativas={letra: letra for letra in "ABCDE"},
        gabarito="A",
        tem_imagem=False,
        imagens=[],
    )


def test_contar_por_area() -> None:
    questoes = [
        _questao(1, AREA_LINGUAGENS),
        _questao(46, AREA_HUMANAS),
        _questao(91, AREA_NATUREZA),
        _questao(92, AREA_NATUREZA),
    ]
    assert contar_por_area(questoes) == {
        AREA_LINGUAGENS: 1,
        AREA_HUMANAS: 1,
        AREA_NATUREZA: 2,
    }
