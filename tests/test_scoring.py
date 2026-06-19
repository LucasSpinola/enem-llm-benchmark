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


def test_intervalo_wilson() -> None:
    baixo, alto = scoring.intervalo_wilson(50, 100)
    assert 0.40 < baixo < 0.41
    assert 0.59 < alto < 0.60
    assert baixo < 0.5 < alto


def test_intervalo_wilson_lista_vazia_e_limites() -> None:
    assert scoring.intervalo_wilson(0, 0) == (0.0, 0.0)
    baixo, alto = scoring.intervalo_wilson(10, 10)  # 100% de acerto
    assert baixo >= 0.0
    assert alto <= 1.0


def test_acuracia_por_modalidade() -> None:
    resultados = [
        _resultado("m", "linguagens", False, True),
        _resultado("m", "linguagens", True, False),
    ]
    modalidade = scoring.acuracia_por_modalidade(resultados)
    assert modalidade["sem imagem"] == 1.0
    assert modalidade["com imagem"] == 0.0


def _resposta(modelo: str, questao_id: str, alternativa: str | None) -> Resultado:
    return Resultado(
        questao_id=questao_id,
        modelo=modelo,
        ano=2025,
        area="linguagens",
        tem_imagem=False,
        alternativa=alternativa,
        gabarito="A",
        acertou=alternativa == "A",
    )


def test_concordancia_entre_modelos() -> None:
    resultados = [
        _resposta("a", "q1", "A"),
        _resposta("b", "q1", "A"),
        _resposta("c", "q1", "B"),
        _resposta("a", "q2", "C"),
        _resposta("b", "q2", "D"),
        _resposta("c", "q2", "C"),
    ]
    pares = scoring.concordancia_entre_modelos(resultados)
    assert pares[("a", "b")] == 0.5  # iguais só em q1
    assert pares[("a", "c")] == 0.5  # iguais só em q2
    assert pares[("b", "c")] == 0.0  # nunca iguais


def test_concordancia_ignora_alternativa_vazia() -> None:
    resultados = [
        _resposta("a", "q1", None),
        _resposta("b", "q1", None),
    ]
    # Duas respostas não extraídas não contam como concordância.
    assert scoring.concordancia_entre_modelos(resultados)[("a", "b")] == 0.0
