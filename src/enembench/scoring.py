"""Pontuação do benchmark, funções puras sobre uma lista de `Resultado`.

Calcula a acurácia geral, por área, por modelo, por modelo e área (a tabela principal) e o recorte
entre questões de texto e questões com imagem. Tudo determinístico e fácil de testar, sem rede.
"""

from collections.abc import Callable, Hashable
from itertools import combinations

from enembench.schema import Resultado


def acertos_e_total(resultados: list[Resultado]) -> tuple[int, int]:
    """Devolve quantos acertos e quantas questões há na lista."""
    acertos = sum(1 for r in resultados if r.acertou)
    return acertos, len(resultados)


def acuracia(resultados: list[Resultado]) -> float:
    """Acurácia geral, de 0 a 1. Devolve 0.0 quando a lista está vazia."""
    acertos, total = acertos_e_total(resultados)
    return acertos / total if total else 0.0


def intervalo_wilson(acertos: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Intervalo de confiança de Wilson para a acurácia, de 0 a 1.

    É mais adequado que o intervalo normal para amostras pequenas e proporções perto de 0 ou 1, que
    é o nosso caso, com poucas dezenas de questões por área. O padrão z=1.96 corresponde a 95%.
    """
    if total == 0:
        return (0.0, 0.0)
    p = acertos / total
    denominador = 1 + z**2 / total
    centro = (p + z**2 / (2 * total)) / denominador
    margem = z * ((p * (1 - p) / total + z**2 / (4 * total**2)) ** 0.5) / denominador
    return (max(0.0, centro - margem), min(1.0, centro + margem))


def _agrupar(
    resultados: list[Resultado], chave: Callable[[Resultado], Hashable]
) -> dict[Hashable, list[Resultado]]:
    """Agrupa os resultados por uma chave qualquer."""
    grupos: dict[Hashable, list[Resultado]] = {}
    for resultado in resultados:
        grupos.setdefault(chave(resultado), []).append(resultado)
    return grupos


def acuracia_por_area(resultados: list[Resultado]) -> dict[str, float]:
    """Acurácia em cada área."""
    return {area: acuracia(grupo) for area, grupo in _agrupar(resultados, lambda r: r.area).items()}


def acuracia_por_modelo(resultados: list[Resultado]) -> dict[str, float]:
    """Acurácia de cada modelo."""
    grupos = _agrupar(resultados, lambda r: r.modelo)
    return {modelo: acuracia(grupo) for modelo, grupo in grupos.items()}


def acuracia_por_modelo_area(resultados: list[Resultado]) -> dict[tuple[str, str], float]:
    """Acurácia por modelo e área, a tabela principal do benchmark."""
    grupos = _agrupar(resultados, lambda r: (r.modelo, r.area))
    return {chave: acuracia(grupo) for chave, grupo in grupos.items()}


def acuracia_por_modalidade(resultados: list[Resultado]) -> dict[str, float]:
    """Acurácia recortada entre questões de texto e questões com imagem."""
    grupos = _agrupar(resultados, lambda r: "com imagem" if r.tem_imagem else "sem imagem")
    return {modalidade: acuracia(grupo) for modalidade, grupo in grupos.items()}


def concordancia_entre_modelos(resultados: list[Resultado]) -> dict[tuple[str, str], float]:
    """Fração de questões em que cada par de modelos deu a mesma alternativa.

    Mede o quanto dois modelos respondem igual, independente de acertar, sobre as questões que ambos
    responderam. Serve à rede de concordância. Função pura, devolve um valor por par ordenado.
    """
    respostas: dict[str, dict[str, str | None]] = {}
    for r in resultados:
        respostas.setdefault(r.modelo, {})[r.questao_id] = r.alternativa
    pares: dict[tuple[str, str], float] = {}
    for a, b in combinations(sorted(respostas), 2):
        comuns = set(respostas[a]) & set(respostas[b])
        if not comuns:
            continue
        iguais = sum(
            1 for q in comuns if respostas[a][q] is not None and respostas[a][q] == respostas[b][q]
        )
        pares[(a, b)] = iguais / len(comuns)
    return pares
