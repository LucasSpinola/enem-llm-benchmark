"""Relatórios do benchmark: gráficos de acurácia e o export dos erros comentados.

Lê o CSV de resultados e desenha três gráficos, acurácia por modelo, acurácia por área por modelo, e
um mapa de calor modelo por área. Também monta o material de erros comentados, as questões que os
modelos erraram, com o raciocínio que cada um deu, recuperado do cache. As funções de seleção são
puras e testáveis, e o desenho usa matplotlib sem display.
"""

import argparse
import csv
import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # sem display, só salva os arquivos
import matplotlib.pyplot as plt  # noqa: E402

from enembench import scoring  # noqa: E402
from enembench.cache import Cache  # noqa: E402
from enembench.dataset import carregar_prova_hf  # noqa: E402
from enembench.pdf_enem import carregar_prova_pdf  # noqa: E402
from enembench.prompt import carregar_imagens, montar_prompt  # noqa: E402
from enembench.schema import AREAS, NOMES_AREAS, Questao, Resultado  # noqa: E402

logger = logging.getLogger(__name__)


def carregar_resultados_csv(caminho: str | Path) -> list[Resultado]:
    """Lê o CSV longo de resultados de volta para uma lista de `Resultado`."""
    resultados: list[Resultado] = []
    with Path(caminho).open(encoding="utf-8", newline="") as arquivo:
        for linha in csv.DictReader(arquivo):
            resultados.append(
                Resultado(
                    questao_id=linha["questao_id"],
                    modelo=linha["modelo"],
                    ano=int(linha["ano"]),
                    area=linha["area"],
                    tem_imagem=linha["tem_imagem"] == "1",
                    alternativa=linha["alternativa"] or None,
                    gabarito=linha["gabarito"],
                    acertou=linha["acertou"] == "1",
                )
            )
    return resultados


def erros(resultados: list[Resultado]) -> list[Resultado]:
    """Filtra os resultados em que o modelo errou. Função pura."""
    return [r for r in resultados if not r.acertou]


def _modelos_e_areas(resultados: list[Resultado]) -> tuple[list[str], list[str]]:
    """Lista os modelos em ordem e as áreas presentes, na ordem padrão do ENEM."""
    modelos = sorted({r.modelo for r in resultados})
    presentes = {r.area for r in resultados}
    areas = [area for area in AREAS if area in presentes]
    return modelos, areas


def grafico_acuracia_por_modelo(resultados: list[Resultado], caminho: str | Path) -> None:
    """Gráfico de barras da acurácia de cada modelo, com intervalo de confiança e baseline."""
    modelos = sorted({r.modelo for r in resultados})
    valores: list[float] = []
    abaixo: list[float] = []
    acima: list[float] = []
    for modelo in modelos:
        do_modelo = [r for r in resultados if r.modelo == modelo]
        acertos, total = scoring.acertos_e_total(do_modelo)
        taxa = acertos / total if total else 0.0
        baixo, alto = scoring.intervalo_wilson(acertos, total)
        valores.append(taxa * 100)
        abaixo.append((taxa - baixo) * 100)
        acima.append((alto - taxa) * 100)

    fig, ax = plt.subplots(figsize=(max(6, len(modelos) * 1.5), 5))
    ax.bar(modelos, valores, color="#4C72B0", yerr=[abaixo, acima], capsize=4)
    ax.axhline(20, linestyle="--", color="gray", linewidth=1, label="acerto ao acaso (20%)")
    ax.set_ylabel("Acurácia (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Acurácia por modelo no ENEM, com intervalo de 95%")
    ax.tick_params(axis="x", rotation=20)
    ax.legend()
    fig.tight_layout()
    fig.savefig(caminho, dpi=120)
    plt.close(fig)


def grafico_acuracia_por_area(resultados: list[Resultado], caminho: str | Path) -> None:
    """Barras agrupadas da acurácia por área, uma série por modelo."""
    tabela = scoring.acuracia_por_modelo_area(resultados)
    modelos, areas = _modelos_e_areas(resultados)
    if not modelos or not areas:
        return
    largura = 0.8 / len(modelos)

    fig, ax = plt.subplots(figsize=(max(7, len(areas) * 1.8), 5))
    for i, modelo in enumerate(modelos):
        valores = [tabela.get((modelo, area), 0.0) * 100 for area in areas]
        posicoes = [j + i * largura for j in range(len(areas))]
        ax.bar(posicoes, valores, largura, label=modelo)
    ax.axhline(20, linestyle="--", color="gray", linewidth=1, label="acerto ao acaso (20%)")
    ax.set_ylabel("Acurácia (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Acurácia por área, por modelo")
    centro = [j + largura * (len(modelos) - 1) / 2 for j in range(len(areas))]
    ax.set_xticks(centro)
    ax.set_xticklabels([NOMES_AREAS[area] for area in areas], rotation=20, ha="right")
    ax.legend()
    fig.tight_layout()
    fig.savefig(caminho, dpi=120)
    plt.close(fig)


def mapa_calor_modelo_area(resultados: list[Resultado], caminho: str | Path) -> None:
    """Mapa de calor da acurácia, modelos nas linhas e áreas nas colunas."""
    tabela = scoring.acuracia_por_modelo_area(resultados)
    modelos, areas = _modelos_e_areas(resultados)
    if not modelos or not areas:
        return
    matriz = [[tabela.get((modelo, area), 0.0) * 100 for area in areas] for modelo in modelos]

    fig, ax = plt.subplots(figsize=(max(6, len(areas) * 1.8), max(3, len(modelos) * 0.8)))
    imagem = ax.imshow(matriz, cmap="YlGn", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(len(areas)))
    ax.set_xticklabels([NOMES_AREAS[area] for area in areas], rotation=20, ha="right")
    ax.set_yticks(range(len(modelos)))
    ax.set_yticklabels(modelos)
    ax.set_title("Acurácia por modelo e área")
    for i in range(len(modelos)):
        for j in range(len(areas)):
            ax.text(j, i, f"{matriz[i][j]:.0f}", ha="center", va="center", color="black")
    fig.colorbar(imagem, ax=ax, label="Acurácia (%)")
    fig.tight_layout()
    fig.savefig(caminho, dpi=120)
    plt.close(fig)


def grafico_modalidade(resultados: list[Resultado], caminho: str | Path) -> None:
    """Barras de texto contra imagem, com intervalo de confiança, para um modelo multimodal."""
    nomes = {"sem imagem": "Questões de texto", "com imagem": "Questões com imagem"}
    rotulos: list[str] = []
    valores: list[float] = []
    abaixo: list[float] = []
    acima: list[float] = []
    for chave in ("sem imagem", "com imagem"):
        do_grupo = [r for r in resultados if r.tem_imagem == (chave == "com imagem")]
        if not do_grupo:
            continue
        acertos, total = scoring.acertos_e_total(do_grupo)
        taxa = acertos / total
        baixo, alto = scoring.intervalo_wilson(acertos, total)
        rotulos.append(f"{nomes[chave]}\n(n={total})")
        valores.append(taxa * 100)
        abaixo.append((taxa - baixo) * 100)
        acima.append((alto - taxa) * 100)
    if not valores:
        return

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.bar(rotulos, valores, color=["#4C72B0", "#DD8452"], yerr=[abaixo, acima], capsize=4)
    ax.axhline(20, linestyle="--", color="gray", linewidth=1, label="acerto ao acaso (20%)")
    ax.set_ylabel("Acurácia (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Texto contra imagem, modelo multimodal")
    ax.legend()
    fig.tight_layout()
    fig.savefig(caminho, dpi=120)
    plt.close(fig)


def gerar_erros_comentados_md(
    resultados: list[Resultado],
    questoes_por_id: dict[str, Questao],
    cache: Cache,
    caminho: str | Path,
    *,
    com_raciocinio: bool = True,
) -> int:
    """Escreve o markdown dos erros comentados e devolve quantos erros foram exportados.

    Para cada questão errada, recupera o raciocínio do cache montando o mesmo prompt da rodada.
    """
    blocos = [
        "# Erros comentados",
        "",
        "Questões que os modelos erraram, com o raciocínio que deram.",
        "",
    ]
    total = 0
    for resultado in erros(resultados):
        questao = questoes_por_id.get(resultado.questao_id)
        if questao is None:
            continue
        prompt = montar_prompt(questao, com_raciocinio)
        imagens = carregar_imagens(questao) if questao.tem_imagem else []
        raciocinio = cache.obter(resultado.modelo, questao.id, prompt, imagens)
        blocos += [
            f"## {questao.id} · {NOMES_AREAS[questao.area]} · modelo {resultado.modelo}",
            "",
            f"**Gabarito:** {resultado.gabarito}  ·  "
            f"**Resposta do modelo:** {resultado.alternativa or 'não extraída'}",
            "",
            "### Enunciado",
            questao.enunciado.strip(),
            "",
            "### Alternativas",
            *[f"- {letra}) {questao.alternativas[letra].strip()}" for letra in "ABCDE"],
            "",
            "### Raciocínio do modelo",
            (raciocinio.strip() if raciocinio else "_Sem raciocínio em cache._"),
            "",
            "---",
            "",
        ]
        total += 1
    Path(caminho).write_text("\n".join(blocos), encoding="utf-8")
    return total


def _carregar_questoes(args: argparse.Namespace) -> dict[str, Questao]:
    if args.fonte == "hf":
        questoes = carregar_prova_hf(args.ano)
    else:
        questoes = carregar_prova_pdf(args.prova, args.gabarito, ano=args.ano, dia=args.dia)
    return {questao.id: questao for questao in questoes}


def _montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="enembench-relatorio", description=__doc__)
    parser.add_argument("--csv", default="results/resultados.csv", help="CSV de resultados")
    parser.add_argument("--fonte", choices=["pdf", "hf"], default="pdf", help="origem das questões")
    parser.add_argument("--prova", default="enem/2025_PV_impresso_D1_CD1.pdf", help="PDF da prova")
    parser.add_argument(
        "--gabarito", default="enem/2025_GB_impresso_D1_CD1.pdf", help="PDF do gabarito"
    )
    parser.add_argument("--ano", type=int, default=2025, help="ano da prova")
    parser.add_argument("--dia", type=int, default=1, help="dia da prova")
    parser.add_argument("--cache", default="cache", help="pasta do cache de respostas")
    parser.add_argument(
        "--saida-dir", default="results", help="onde salvar os gráficos e o markdown"
    )
    parser.add_argument("--curto", action="store_true", help="a rodada usou o prompt curto")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Gera os gráficos e o export de erros comentados a partir do CSV de resultados."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = _montar_parser().parse_args(argv)

    resultados = carregar_resultados_csv(args.csv)
    if not resultados:
        print("CSV de resultados vazio. Rode o benchmark antes de gerar o relatório.")
        return 1

    saida = Path(args.saida_dir)
    saida.mkdir(parents=True, exist_ok=True)
    grafico_acuracia_por_modelo(resultados, saida / "acuracia_por_modelo.png")
    grafico_acuracia_por_area(resultados, saida / "acuracia_por_area.png")
    mapa_calor_modelo_area(resultados, saida / "mapa_calor_modelo_area.png")

    questoes = _carregar_questoes(args)
    total_erros = gerar_erros_comentados_md(
        resultados,
        questoes,
        Cache(Path(args.cache)),
        saida / "erros_comentados.md",
        com_raciocinio=not args.curto,
    )

    print(f"Gráficos salvos em {saida}/")
    print(f"Erros comentados: {total_erros} questões em {saida}/erros_comentados.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
