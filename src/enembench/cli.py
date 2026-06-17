"""Ponto de entrada de linha de comando do benchmark.

Roda os modelos configurados sobre uma prova do ENEM, salva os resultados em CSV e imprime a
acurácia geral e por área. As respostas ficam em cache, então repetir o comando não gasta cota.
"""

import argparse
import logging
from pathlib import Path

from dotenv import load_dotenv

from enembench import scoring
from enembench.cache import Cache
from enembench.dataset import carregar_prova_hf
from enembench.pdf_enem import carregar_prova_pdf
from enembench.runner import carregar_modelos, executar, salvar_resultados_csv
from enembench.schema import NOMES_AREAS, Questao, Resultado

logger = logging.getLogger(__name__)

_PROVA_PADRAO = "enem/2025_PV_impresso_D1_CD1.pdf"
_GABARITO_PADRAO = "enem/2025_GB_impresso_D1_CD1.pdf"


def _montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="enembench", description=__doc__)
    parser.add_argument("--fonte", choices=["pdf", "hf"], default="pdf", help="origem das questões")
    parser.add_argument("--prova", default=_PROVA_PADRAO, help="PDF da prova (fonte pdf)")
    parser.add_argument("--gabarito", default=_GABARITO_PADRAO, help="PDF do gabarito (fonte pdf)")
    parser.add_argument("--ano", type=int, default=2025, help="ano da prova")
    parser.add_argument("--dia", type=int, default=1, help="dia da prova (fonte pdf)")
    parser.add_argument("--config", default="config/models.yaml", help="lista de modelos")
    parser.add_argument("--modelos", default="", help="ids a rodar, separados por vírgula")
    parser.add_argument("--limite", type=int, default=0, help="máximo de questões, 0 para todas")
    parser.add_argument("--so-texto", action="store_true", help="ignora questões com imagem")
    parser.add_argument("--curto", action="store_true", help="prompt curto, sem raciocínio")
    parser.add_argument("--saida", default="results/resultados.csv", help="CSV de saída")
    parser.add_argument("--cache", default="cache", help="pasta do cache de respostas")
    return parser


def _carregar_questoes(args: argparse.Namespace) -> list[Questao]:
    if args.fonte == "hf":
        questoes = carregar_prova_hf(args.ano)
    else:
        questoes = carregar_prova_pdf(args.prova, args.gabarito, ano=args.ano, dia=args.dia)
    if args.limite > 0:
        questoes = questoes[: args.limite]
    return questoes


def _imprimir_resumo(resultados: list[Resultado]) -> None:
    acertos, total = scoring.acertos_e_total(resultados)
    if total == 0:
        print("Nenhum resultado para resumir.")
        return
    print(f"\nAcurácia geral: {scoring.acuracia(resultados):.1%} ({acertos}/{total})")

    print("\nPor modelo:")
    for modelo, taxa in sorted(scoring.acuracia_por_modelo(resultados).items()):
        print(f"  {modelo:24s} {taxa:6.1%}")

    print("\nPor área:")
    por_area = scoring.acuracia_por_area(resultados)
    for area, taxa in sorted(por_area.items()):
        print(f"  {NOMES_AREAS.get(area, area):24s} {taxa:6.1%}")

    modalidade = scoring.acuracia_por_modalidade(resultados)
    if len(modalidade) > 1:
        print("\nTexto contra imagem:")
        for nome, taxa in sorted(modalidade.items()):
            print(f"  {nome:24s} {taxa:6.1%}")


def main(argv: list[str] | None = None) -> int:
    """Executa o benchmark a partir dos argumentos de linha de comando."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    load_dotenv()
    args = _montar_parser().parse_args(argv)

    questoes = _carregar_questoes(args)
    modelos = carregar_modelos(args.config)
    if args.modelos:
        escolhidos = {m.strip() for m in args.modelos.split(",") if m.strip()}
        modelos = [m for m in modelos if m.id in escolhidos]
    if not modelos:
        print("Nenhum modelo selecionado. Confira o --config e o --modelos.")
        return 1

    logger.info("Avaliando %d modelos em %d questões", len(modelos), len(questoes))
    resultados = executar(
        modelos,
        questoes,
        Cache(Path(args.cache)),
        com_raciocinio=not args.curto,
        so_texto=args.so_texto,
    )

    salvar_resultados_csv(resultados, args.saida)
    print(f"Resultados salvos em {args.saida}")
    _imprimir_resumo(resultados)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
