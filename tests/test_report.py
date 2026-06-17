"""Testes das funções puras do relatório: filtro de erros e ida e volta do CSV."""

from pathlib import Path

from enembench.report import carregar_resultados_csv, erros
from enembench.runner import salvar_resultados_csv
from enembench.schema import Resultado


def _resultado(qid: str, acertou: bool, alternativa: str | None = "A") -> Resultado:
    return Resultado(
        questao_id=qid,
        modelo="m",
        ano=2025,
        area="linguagens",
        tem_imagem=False,
        alternativa=alternativa,
        gabarito="A",
        acertou=acertou,
    )


def test_erros_filtra_so_os_errados() -> None:
    resultados = [_resultado("q1", True), _resultado("q2", False), _resultado("q3", False)]
    assert [r.questao_id for r in erros(resultados)] == ["q2", "q3"]


def test_csv_ida_e_volta(tmp_path: Path) -> None:
    originais = [
        Resultado("q1", "gemini", 2025, "linguagens", False, "C", "C", True),
        Resultado("q2", "gemini", 2025, "humanas", True, None, "B", False),
    ]
    caminho = tmp_path / "resultados.csv"
    salvar_resultados_csv(originais, caminho)

    lidos = carregar_resultados_csv(caminho)

    assert lidos == originais
    assert lidos[1].alternativa is None  # campo vazio volta como None
    assert lidos[1].tem_imagem is True
