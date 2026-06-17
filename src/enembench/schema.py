"""Modelo de dados único do benchmark, independente do dataset de origem.

Toda questão, venha de onde vier, é normalizada para `Questao`. As respostas dos modelos viram
`RespostaModelo`, e o cruzamento de resposta com gabarito vira `Resultado`, a linha da tabela
longa que alimenta as métricas e os gráficos.
"""

from dataclasses import dataclass

# As quatro áreas do ENEM, com rótulos padronizados para os gráficos ficarem consistentes.
AREA_LINGUAGENS = "linguagens"
AREA_HUMANAS = "humanas"
AREA_NATUREZA = "natureza"
AREA_MATEMATICA = "matematica"

AREAS: tuple[str, ...] = (AREA_LINGUAGENS, AREA_HUMANAS, AREA_NATUREZA, AREA_MATEMATICA)

# Os rótulos longos, para títulos e legendas dos gráficos.
NOMES_AREAS: dict[str, str] = {
    AREA_LINGUAGENS: "Linguagens",
    AREA_HUMANAS: "Ciências Humanas",
    AREA_NATUREZA: "Ciências da Natureza",
    AREA_MATEMATICA: "Matemática",
}


@dataclass(frozen=True)
class Questao:
    """Uma questão do ENEM já normalizada."""

    id: str  # identificador estável, ex: "enem-2023-45"
    ano: int
    area: str  # um dos valores de AREAS
    enunciado: str
    alternativas: dict[str, str]  # {"A": "...", "B": "...", ...}
    gabarito: str  # "A".."E"
    tem_imagem: bool
    imagens: list[str]  # caminhos ou URLs das imagens, vazio se não houver


@dataclass(frozen=True)
class RespostaModelo:
    """O que um modelo devolveu para uma questão."""

    questao_id: str
    modelo: str
    resposta_crua: str  # texto integral devolvido pelo modelo
    alternativa: str | None  # letra extraída, None se não deu para extrair
    latencia_s: float


@dataclass(frozen=True)
class Resultado:
    """Uma linha da tabela longa: resposta de um modelo a uma questão, já pontuada."""

    questao_id: str
    modelo: str
    ano: int
    area: str
    tem_imagem: bool
    alternativa: str | None
    gabarito: str
    acertou: bool
