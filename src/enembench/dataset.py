"""Fonte de dados Hugging Face: o dataset aberto maritaca-ai/enem (licença Apache 2.0).

Cobre o ENEM de 2022, 2023 e 2024, com imagens como URLs e descrições textuais. É mantida como
fonte opcional ao lado da fonte de PDF do INEP (`pdf_enem.py`); ambas devolvem `list[Questao]`. Os
detalhes da fonte e da licença estão em `data/README.md`.

A normalização separa funções puras (sem rede), testáveis isoladamente, da função de carga que fala
com o Hugging Face. As imagens ficam guardadas como URLs, o download dos bytes vem mais adiante.
"""

import logging
import re

from datasets import load_dataset

from enembench.normalizacao import alternativas_para_dict, area_de_numero
from enembench.schema import Questao

logger = logging.getLogger(__name__)

DATASET_HF = "maritaca-ai/enem"
ANOS_DISPONIVEIS: tuple[int, ...] = (2022, 2023, 2024)

_NUMERO_NO_ID = re.compile(r"(\d+)")


def _numero_da_questao(id_bruto: str) -> int:
    """Extrai o número inteiro do id de origem, no formato 'questao_NN'."""
    achado = _NUMERO_NO_ID.search(id_bruto)
    if achado is None:
        raise ValueError(f"Id de questão sem número: {id_bruto!r}")
    return int(achado.group(1))


def _linha_para_questao(linha: dict, ano: int) -> Questao:
    """Normaliza uma linha do dataset maritaca-ai/enem para `Questao`. Função pura, sem rede."""
    numero = _numero_da_questao(linha["id"])
    return Questao(
        id=f"enem-{ano}-{numero:02d}",
        ano=ano,
        area=area_de_numero(numero),
        enunciado=linha["question"],
        alternativas=alternativas_para_dict(linha["alternatives"]),
        gabarito=str(linha["label"]).strip().upper(),
        tem_imagem=bool(linha["IU"]),
        imagens=list(linha["figures"]),
    )


def carregar_prova_hf(ano: int) -> list[Questao]:
    """Carrega e normaliza a prova do ENEM de um ano em uma lista de `Questao`.

    Baixa do Hugging Face na primeira vez e reusa o cache local nas próximas.
    """
    if ano not in ANOS_DISPONIVEIS:
        raise ValueError(f"Ano {ano} indisponível. Anos cobertos: {ANOS_DISPONIVEIS}")
    dados = load_dataset(DATASET_HF, str(ano), split="train")
    questoes = [_linha_para_questao(linha, ano) for linha in dados]
    logger.info("Carregadas %d questões do ENEM %d (Hugging Face)", len(questoes), ano)
    return questoes
