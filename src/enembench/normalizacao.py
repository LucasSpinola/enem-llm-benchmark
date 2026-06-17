"""Helpers puros de normalização, compartilhados pelas fontes de dados.

Toda fonte (Hugging Face, PDF do INEP) converte suas questões para `schema.Questao` reusando estas
funções, então a derivação da área e o mapeamento das alternativas ficam num lugar só, sem rede e
sem leitura de arquivo, fáceis de testar.
"""

from collections import defaultdict

from enembench.schema import (
    AREA_HUMANAS,
    AREA_LINGUAGENS,
    AREA_MATEMATICA,
    AREA_NATUREZA,
    Questao,
)

# As cinco letras das alternativas, na ordem.
LETRAS: tuple[str, ...] = ("A", "B", "C", "D", "E")


def area_de_numero(numero: int) -> str:
    """Deriva a área do ENEM a partir do número da questão, de 1 a 180.

    Segue a estrutura fixa da prova: 1 a 45 linguagens, 46 a 90 ciências humanas, 91 a 135
    ciências da natureza, e 136 a 180 matemática. Levanta ValueError fora desse intervalo.
    """
    if 1 <= numero <= 45:
        return AREA_LINGUAGENS
    if 46 <= numero <= 90:
        return AREA_HUMANAS
    if 91 <= numero <= 135:
        return AREA_NATUREZA
    if 136 <= numero <= 180:
        return AREA_MATEMATICA
    raise ValueError(f"Número de questão fora do intervalo 1 a 180: {numero}")


def alternativas_para_dict(alternativas: list[str]) -> dict[str, str]:
    """Mapeia a lista de cinco alternativas para o dicionário {'A': ..., ..., 'E': ...}."""
    if len(alternativas) != len(LETRAS):
        raise ValueError(f"Esperava {len(LETRAS)} alternativas, recebi {len(alternativas)}")
    return dict(zip(LETRAS, alternativas, strict=True))


def contar_por_area(questoes: list[Questao]) -> dict[str, int]:
    """Conta quantas questões há em cada área, útil para conferir o carregamento."""
    contagem: dict[str, int] = defaultdict(int)
    for questao in questoes:
        contagem[questao.area] += 1
    return dict(contagem)
