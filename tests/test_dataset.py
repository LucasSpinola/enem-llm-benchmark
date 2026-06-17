"""Testes das funções puras da fonte Hugging Face, sem nenhuma chamada de rede."""

import pytest

from enembench.dataset import _linha_para_questao, _numero_da_questao
from enembench.schema import AREA_LINGUAGENS, AREA_MATEMATICA


def test_numero_da_questao() -> None:
    assert _numero_da_questao("questao_07") == 7
    assert _numero_da_questao("questao_180") == 180


def test_numero_da_questao_sem_numero() -> None:
    with pytest.raises(ValueError):
        _numero_da_questao("questao")


def test_linha_para_questao_textual() -> None:
    linha = {
        "id": "questao_05",
        "question": "Qual o sujeito da oração?",
        "alternatives": ["o gato", "o rato", "a casa", "o muro", "a rua"],
        "label": "b",
        "IU": False,
        "figures": [],
    }
    questao = _linha_para_questao(linha, 2023)

    assert questao.id == "enem-2023-05"
    assert questao.ano == 2023
    assert questao.area == AREA_LINGUAGENS
    assert questao.gabarito == "B"  # normalizado para maiúscula
    assert questao.tem_imagem is False
    assert questao.imagens == []
    assert questao.alternativas["A"] == "o gato"


def test_linha_para_questao_com_imagem() -> None:
    linha = {
        "id": "questao_136",
        "question": "Considere o gráfico a seguir.",
        "alternatives": ["1", "2", "3", "4", "5"],
        "label": "D",
        "IU": True,
        "figures": ["https://exemplo.test/figura.png"],
    }
    questao = _linha_para_questao(linha, 2024)

    assert questao.id == "enem-2024-136"
    assert questao.area == AREA_MATEMATICA
    assert questao.tem_imagem is True
    assert questao.imagens == ["https://exemplo.test/figura.png"]
