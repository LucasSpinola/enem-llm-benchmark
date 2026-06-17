"""Orquestra a avaliação de modelos sobre questões, com cache e limite de taxa.

Para cada par modelo e questão, monta o prompt, consulta o cache, e só chama a API se for preciso.
O modelo de texto puro pula as questões com imagem. As respostas cruas vão para o cache, que serve
os erros comentados depois, e os resultados pontuados saem como uma tabela longa em CSV.
"""

import csv
import logging
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import yaml

from enembench.cache import Cache
from enembench.parsing import extrair_alternativa
from enembench.prompt import carregar_imagens, montar_prompt
from enembench.providers.base import Provider, criar_provedor
from enembench.schema import Questao, Resultado

logger = logging.getLogger(__name__)

# Intervalo padrão entre chamadas, em segundos, por provedor, para respeitar o free tier.
_INTERVALO_PADRAO: dict[str, float] = {"gemini": 4.0, "groq": 2.0, "openrouter": 3.0, "fake": 0.0}


@dataclass(frozen=True)
class ModeloConfig:
    """Uma entrada do config/models.yaml."""

    id: str
    provider: str
    model: str
    multimodal: bool


def carregar_modelos(caminho: str | Path) -> list[ModeloConfig]:
    """Lê o config/models.yaml e devolve a lista de modelos a avaliar."""
    dados = yaml.safe_load(Path(caminho).read_text(encoding="utf-8")) or []
    return [
        ModeloConfig(
            id=item["id"],
            provider=item["provider"],
            model=item["model"],
            multimodal=bool(item.get("multimodal", False)),
        )
        for item in dados
    ]


class LimitadorTaxa:
    """Garante um intervalo mínimo entre chamadas, para não estourar o limite do provedor."""

    def __init__(self, intervalo_s: float) -> None:
        self.intervalo_s = intervalo_s
        self._ultimo = 0.0

    def aguardar(self) -> None:
        """Dorme o tempo que faltar para respeitar o intervalo desde a última chamada."""
        espera = self.intervalo_s - (time.monotonic() - self._ultimo)
        if espera > 0:
            time.sleep(espera)
        self._ultimo = time.monotonic()


def _deve_pular(config: ModeloConfig, questao: Questao, so_texto: bool) -> bool:
    """Diz se um par modelo e questão deve ser pulado, por imagem ou por filtro de texto."""
    if questao.tem_imagem and not config.multimodal:
        return True
    return bool(so_texto and questao.tem_imagem)


def executar_modelo(
    config: ModeloConfig,
    provedor: Provider,
    questoes: Iterable[Questao],
    cache: Cache,
    *,
    com_raciocinio: bool = True,
    limitador: LimitadorTaxa | None = None,
    so_texto: bool = False,
) -> list[Resultado]:
    """Avalia um modelo sobre as questões, usando o cache e devolvendo os resultados pontuados.

    Uma falha em uma questão, como um erro de cota ou de rede, vira um resultado sem alternativa em
    vez de derrubar o restante, e não vai para o cache, para ser tentada de novo numa próxima vez.
    """
    resultados: list[Resultado] = []
    for questao in questoes:
        if _deve_pular(config, questao, so_texto):
            continue
        prompt = montar_prompt(questao, com_raciocinio)
        imagens = carregar_imagens(questao) if (config.multimodal and questao.tem_imagem) else []

        resposta_crua = cache.obter(config.id, questao.id, prompt, imagens)
        if resposta_crua is None:
            if limitador is not None:
                limitador.aguardar()
            inicio = time.monotonic()
            try:
                resposta_crua = provedor.responder(prompt, imagens or None)
            except Exception as erro:
                logger.warning("Falha na questão %s do modelo %s: %s", questao.id, config.id, erro)
                resultados.append(_montar_resultado(config, questao, None))
                continue
            latencia_s = time.monotonic() - inicio
            cache.guardar(config.id, questao.id, prompt, resposta_crua, latencia_s, imagens)

        alternativa = extrair_alternativa(resposta_crua)
        resultados.append(_montar_resultado(config, questao, alternativa))
    return resultados


def _montar_resultado(config: ModeloConfig, questao: Questao, alternativa: str | None) -> Resultado:
    """Cruza a alternativa extraída com o gabarito e monta a linha de resultado."""
    return Resultado(
        questao_id=questao.id,
        modelo=config.id,
        ano=questao.ano,
        area=questao.area,
        tem_imagem=questao.tem_imagem,
        alternativa=alternativa,
        gabarito=questao.gabarito,
        acertou=alternativa == questao.gabarito,
    )


def executar(
    modelos: Iterable[ModeloConfig],
    questoes: list[Questao],
    cache: Cache,
    *,
    com_raciocinio: bool = True,
    so_texto: bool = False,
    intervalos: dict[str, float] | None = None,
) -> list[Resultado]:
    """Avalia vários modelos, montando cada provedor pelo registro e pulando os que falharem."""
    intervalos = intervalos or _INTERVALO_PADRAO
    resultados: list[Resultado] = []
    for config in modelos:
        try:
            provedor = criar_provedor(config.provider, config.model)
        except Exception as erro:
            # Falha de chave ou de rede em um modelo não derruba a avaliação dos outros.
            logger.warning("Pulando modelo %s: %s", config.id, erro)
            continue
        limitador = LimitadorTaxa(intervalos.get(config.provider, 0.0))
        resultados.extend(
            executar_modelo(
                config,
                provedor,
                questoes,
                cache,
                com_raciocinio=com_raciocinio,
                limitador=limitador,
                so_texto=so_texto,
            )
        )
        logger.info("Modelo %s avaliado em %d questões", config.id, len(questoes))
    return resultados


_CABECALHO_CSV = [
    "questao_id",
    "modelo",
    "ano",
    "area",
    "tem_imagem",
    "alternativa",
    "gabarito",
    "acertou",
]


def salvar_resultados_csv(resultados: list[Resultado], caminho: str | Path) -> None:
    """Salva os resultados como uma tabela longa em CSV, uma linha por modelo e questão."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(_CABECALHO_CSV)
        for r in resultados:
            escritor.writerow(
                [
                    r.questao_id,
                    r.modelo,
                    r.ano,
                    r.area,
                    int(r.tem_imagem),
                    r.alternativa or "",
                    r.gabarito,
                    int(r.acertou),
                ]
            )
