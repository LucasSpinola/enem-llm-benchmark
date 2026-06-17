"""Testes das funções de pontuação, com um conjunto pequeno conferido à mão."""

from enembench import scoring
from enembench.schema import Resultado


def _resultado(modelo: str, area: str, tem_imagem: bool, acertou: bool) -> Resultado:
    return Resultado(
        questao_id="x",
        modelo=modelo,
        ano=2025,
        area=area,
        tem_imagem=tem_imagem,
        alternativa="A",
        gabarito="A" if acertou else "B",
        acertou=acertou,
    )


def test_acuracia_geral() -> None:
    resultados = [
        _resultado("m", "linguagens", False, True),
        _resultado("m", "linguagens", False, False),
    ]
    assert scoring.acuracia(resultados) == 0.5
    assert scoring.acertos_e_total(resultados) == (1, 2)


def test_acuracia_lista_vazia() -> None:
    assert scoring.acuracia([]) == 0.0
    assert scoring.acertos_e_total([]) == (0, 0)


def test_acuracia_por_area() -> None:
    resultados = [
        _resultado("m", "linguagens", False, True),
        _resultado("m", "humanas", False, False),
        _resultado("m", "humanas", False, True),
    ]
    assert scoring.acuracia_por_area(resultados) == {"linguagens": 1.0, "humanas": 0.5}


def test_acuracia_por_modelo_area() -> None:
    resultados = [
        _resultado("gemini", "linguagens", False, True),
        _resultado("gemini", "linguagens", False, False),
        _resultado("llama", "linguagens", False, True),
    ]
    tabela = scoring.acuracia_por_modelo_area(resultados)
    assert tabela[("gemini", "linguagens")] == 0.5
    assert tabela[("llama", "linguagens")] == 1.0


def test_acuracia_por_modalidade() -> None:
    resultados = [
        _resultado("m", "linguagens", False, True),
        _resultado("m", "linguagens", True, False),
    ]
    modalidade = scoring.acuracia_por_modalidade(resultados)
    assert modalidade["sem imagem"] == 1.0
    assert modalidade["com imagem"] == 0.0
