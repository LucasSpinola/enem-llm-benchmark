"""Extração da alternativa A a E da resposta crua de um modelo. Função pura e robusta.

A ideia é tolerar respostas bagunçadas: às vezes o modelo escreve "Resposta: C", às vezes
"alternativa correta é a letra D", às vezes só a letra, e às vezes explica antes de concluir. O
cuidado central é não confundir a letra da resposta com o artigo "a" ou a conjunção "e", que em
português são palavras de uma letra. Por isso a letra solta só conta em maiúscula, e a letra
minúscula só vale logo após um separador, como em "Resposta: c". Se nada casar, devolve None, o que
conta como erro, não como exceção.
"""

import re

# Palavras-chave que costumam anteceder a letra. Conclusões ("resposta", "gabarito") vêm primeiro,
# pois "alternativa" aparece muito no meio do raciocínio, sobre opções que o modelo descarta.
_PALAVRAS = r"(?i:resposta|gabarito|alternativa|letra|op[çc][ãa]o)"
# 1. Palavra-chave, separador e a letra. O separador obrigatório evita casar o artigo "a".
_PADRAO_COM_SEPARADOR = re.compile(rf"{_PALAVRAS}\s*[:\-–=]\s*([A-Ea-e])\b")
# 2. Palavra-chave, espaço e a letra em maiúscula. A maiúscula evita artigos e conjunções.
_PADRAO_SEM_SEPARADOR = re.compile(rf"{_PALAVRAS}\s+([A-E])\b")
# 3. Último recurso: uma letra A a E isolada e em maiúscula.
_PADRAO_LETRA_ISOLADA = re.compile(r"\b([A-E])\b")


def extrair_alternativa(texto: str) -> str | None:
    """Extrai a alternativa A a E da resposta do modelo, ou None se não encontrar.

    Tenta os padrões do mais confiável ao menos e, em cada um, fica com a última ocorrência, pois o
    modelo costuma concluir no fim.
    """
    if not texto:
        return None
    alvo = texto.strip()
    for padrao in (_PADRAO_COM_SEPARADOR, _PADRAO_SEM_SEPARADOR, _PADRAO_LETRA_ISOLADA):
        achados = padrao.findall(alvo)
        if achados:
            return achados[-1].upper()
    return None
