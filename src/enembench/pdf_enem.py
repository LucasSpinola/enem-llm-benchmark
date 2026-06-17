"""Fonte de dados PDF: provas oficiais do ENEM publicadas pelo INEP.

Lê o caderno de prova e o gabarito em PDF e normaliza as questões para `schema.Questao`. A prova vem
em duas colunas, então o texto é lido coluna a coluna por coordenada, e as figuras das questões são
recortadas para PNG, para os modelos multimodais. Veja `data/README.md` para a fonte e a licença.

O módulo separa funções puras (segmentação, alternativas, gabarito, montagem), testáveis sem rede e
sem arquivo, das funções de IO que abrem o PDF com pdfplumber e rasterizam com pypdfium2.
"""

import logging
import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber
import pypdfium2 as pdfium

from enembench.normalizacao import LETRAS, area_de_numero
from enembench.schema import Questao

logger = logging.getLogger(__name__)

# Cabeçalho de questão, ex: "QUESTÃO 11" ou "QUESTÃO 136" (o Dia 2 vai de 91 a 180, com 3 dígitos).
# O glifo do ã pode vir maiúsculo ou minúsculo na fonte.
_RE_CABECALHO = re.compile(r"^quest[ãa]o\s+0*(\d{1,3})\b", re.IGNORECASE)
# A palavra "QUESTÃO" isolada, pois em extract_words ela vem separada do número.
_RE_PALAVRA_QUESTAO = re.compile(r"^quest[ãa]o$", re.IGNORECASE)
# Marcador de alternativa no início da linha. O texto é opcional, pois em algumas questões as
# alternativas são imagens e a linha tem só a letra, ex: "A" sozinho.
_RE_ALTERNATIVA = re.compile(r"^([A-E])(?:\s+(\S.*))?$")
# Ruído de página: marca d'água repetida, código de barras e rodapé de qualquer caderno.
_RE_MARCA_DAGUA = re.compile(r"ENEM2025ENEM2025", re.IGNORECASE)
_RE_CODIGO_BARRAS = re.compile(r"^\*\d+[A-Z]{2}\d+\*$")
_RE_SO_NUMERO = re.compile(r"^\d{1,2}$")
_RE_RODAPE = re.compile(r"CADERNO\s+\d", re.IGNORECASE)
_RE_REDACAO = re.compile(r"proposta\s+de\s+reda[çc][ãa]o", re.IGNORECASE)


def linha_e_ruido(linha: str) -> bool:
    """Diz se uma linha é puro ruído de página (marca d'água, código de barras, rodapé, número)."""
    texto = linha.strip()
    if not texto:
        return True
    if _RE_MARCA_DAGUA.search(texto):
        return True
    if _RE_CODIGO_BARRAS.match(texto):
        return True
    if _RE_SO_NUMERO.match(texto):
        return True
    if _RE_RODAPE.search(texto):
        return True
    return False


@dataclass(frozen=True)
class BlocoQuestao:
    """Um trecho bruto de uma questão: o número e as linhas de texto, sem o cabeçalho."""

    numero: int
    linhas: list[str]


def segmentar_questoes(linhas: list[str]) -> list[BlocoQuestao]:
    """Quebra as linhas já em ordem de leitura em blocos por questão.

    Cada bloco vai do cabeçalho "QUESTÃO N" até o próximo cabeçalho ou o início da redação. Mantém
    apenas a primeira ocorrência de cada número, o que descarta a versão em espanhol das questões 1
    a 5, já que a versão em inglês aparece antes.
    """
    blocos: list[BlocoQuestao] = []
    vistos: set[int] = set()
    numero_atual: int | None = None
    acumulado: list[str] = []

    def fechar() -> None:
        if numero_atual is not None and numero_atual not in vistos:
            blocos.append(BlocoQuestao(numero_atual, acumulado.copy()))
            vistos.add(numero_atual)

    for linha in linhas:
        cabecalho = _RE_CABECALHO.match(linha.strip())
        if cabecalho:
            fechar()
            numero_atual = int(cabecalho.group(1))
            acumulado = []
            continue
        if _RE_REDACAO.search(linha):
            fechar()
            numero_atual = None
            acumulado = []
            continue
        if numero_atual is not None:
            acumulado.append(linha)
    fechar()
    return blocos


def extrair_alternativas(linhas: list[str]) -> tuple[str, dict[str, str]]:
    """Separa o enunciado das cinco alternativas em um bloco de questão.

    As alternativas são a primeira sequência completa de marcadores A, B, C, D e E em ordem. Linhas
    sem marcador depois de uma alternativa são continuação dela. Levanta ValueError se não achar as
    cinco. Devolve (enunciado, {"A": ..., ..., "E": ...}).
    """
    marcadores: list[tuple[int, str, str]] = []  # (indice, letra, resto)
    for indice, linha in enumerate(linhas):
        casa = _RE_ALTERNATIVA.match(linha.strip())
        if casa:
            marcadores.append((indice, casa.group(1), casa.group(2) or ""))

    inicio = _primeira_sequencia_abcde(marcadores)
    if inicio is None:
        raise ValueError("Não encontrei a sequência de alternativas A a E no bloco")

    selecionados = inicio  # cinco tuplas (indice, letra, resto), uma por letra
    idx_primeira = selecionados[0][0]
    enunciado = " ".join(linha.strip() for linha in linhas[:idx_primeira]).strip()

    alternativas: dict[str, str] = {}
    for ordem, (indice, letra, resto) in enumerate(selecionados):
        fim = selecionados[ordem + 1][0] if ordem + 1 < len(selecionados) else len(linhas)
        continuacao = [linha.strip() for linha in linhas[indice + 1 : fim]]
        texto = " ".join([resto, *continuacao]).strip()
        alternativas[letra] = texto
    return enunciado, alternativas


def _primeira_sequencia_abcde(
    marcadores: list[tuple[int, str, str]],
) -> list[tuple[int, str, str]] | None:
    """Acha a primeira sequência A, B, C, D, E em ordem crescente de índice."""
    for i, marcador in enumerate(marcadores):
        if marcador[1] != "A":
            continue
        sequencia = [marcador]
        esperado = 1  # aponta para a próxima letra esperada em LETRAS
        for proximo in marcadores[i + 1 :]:
            if proximo[1] == LETRAS[esperado]:
                sequencia.append(proximo)
                esperado += 1
                if esperado == len(LETRAS):
                    return sequencia
    return None


def montar_questao(
    bloco: BlocoQuestao,
    gabarito: dict[int, str],
    ano: int,
    *,
    tem_imagem: bool,
    imagens: list[str],
) -> Questao:
    """Monta uma `Questao` a partir de um bloco, do gabarito e da info de imagem. Função pura."""
    if bloco.numero not in gabarito:
        raise ValueError(f"Questão {bloco.numero} sem gabarito")
    enunciado, alternativas = extrair_alternativas(bloco.linhas)
    if len(alternativas) != len(LETRAS):
        raise ValueError(f"Questão {bloco.numero} com {len(alternativas)} alternativas")
    return Questao(
        id=f"enem-{ano}-{bloco.numero:02d}",
        ano=ano,
        area=area_de_numero(bloco.numero),
        enunciado=enunciado,
        alternativas=alternativas,
        gabarito=gabarito[bloco.numero].strip().upper(),
        tem_imagem=tem_imagem,
        imagens=imagens,
    )


def parse_gabarito(linhas: list[str], *, lingua: str = "ingles") -> dict[int, str]:
    """Lê as linhas do gabarito e devolve {numero: letra}.

    Cada linha pode conter um ou mais pares número seguido de letras. Nas questões 1 a 5 há duas
    letras, inglês e depois espanhol, e escolhe-se a do idioma pedido. Nas demais há uma letra só.
    """
    indice_lingua = 1 if lingua == "espanhol" else 0
    respostas: dict[int, str] = {}
    for linha in linhas:
        tokens = linha.strip().split()
        i = 0
        while i < len(tokens):
            if tokens[i].isdigit():
                numero = int(tokens[i])
                letras: list[str] = []
                j = i + 1
                while j < len(tokens) and tokens[j] in LETRAS:
                    letras.append(tokens[j])
                    j += 1
                if letras and 1 <= numero <= 180:
                    escolha = letras[indice_lingua] if indice_lingua < len(letras) else letras[0]
                    respostas[numero] = escolha
                i = j
            else:
                i += 1
    return respostas


# --------------------------------------------------------------------------------------------------
# Camada de IO: leitura do PDF e rasterização das figuras.
# --------------------------------------------------------------------------------------------------

# Margens em pontos para recortar cada coluna, ignorando cabeçalho e rodapé da página.
_MARGEM_TOPO = 95.0
_MARGEM_BASE = 35.0
# Dimensão mínima de uma imagem raster para contar como figura, ignora ícones e enfeites.
_MIN_LADO_FIGURA = 45.0
# Folga ao redor da figura ao recortar, em pontos.
_FOLGA_FIGURA = 6.0

# Detecção de figura vetorial (gráficos, mapas, figuras geométricas), além das imagens raster.
# Objetos menores que isto são marcadores de alternativa e ícones, descartados.
_MIN_OBJ_VETOR = 15.0
# Espessura mínima, para descartar linhas e réguas finas.
_ESPESSURA_MIN = 3.0
# Lado mínimo do aglomerado de tinta vetorial para valer como figura.
_MIN_LADO_VETOR = 60.0
# Fração máxima de texto dentro do aglomerado. Acima disto é caixa de texto ou tabela, não figura.
_MAX_FRACAO_TEXTO_FIGURA = 0.12


def _linhas_ordenadas(pdf: pdfplumber.PDF) -> list[str]:
    """Extrai o texto de toda a prova em ordem de leitura, coluna esquerda e depois direita."""
    linhas: list[str] = []
    for pagina in pdf.pages:
        meio = pagina.width / 2
        colunas = [(0.0, meio), (meio, pagina.width)]
        for x0, x1 in colunas:
            recorte = pagina.crop((x0, _MARGEM_TOPO, x1, pagina.height - _MARGEM_BASE))
            texto = recorte.extract_text() or ""
            for linha in texto.splitlines():
                if not linha_e_ruido(linha):
                    linhas.append(linha)
    return linhas


def _cabecalhos_com_coords(pdf: pdfplumber.PDF) -> list[tuple[int, int, int, float]]:
    """Localiza cada cabeçalho de questão: (numero, indice_pagina, coluna, top). Coluna 0 ou 1.

    O cabeçalho vem como dois tokens, "QUESTÃO" e o número, então casamos a palavra "QUESTÃO" com o
    token de dígitos seguinte.
    """
    cabecalhos: list[tuple[int, int, int, float]] = []
    for indice, pagina in enumerate(pdf.pages):
        meio = pagina.width / 2
        for x0, x1 in [(0.0, meio), (meio, pagina.width)]:
            coluna = 0 if x0 == 0.0 else 1
            recorte = pagina.crop((x0, _MARGEM_TOPO, x1, pagina.height - _MARGEM_BASE))
            palavras = recorte.extract_words()
            for atual, proxima in zip(palavras, palavras[1:], strict=False):
                if _RE_PALAVRA_QUESTAO.match(atual["text"]) and proxima["text"].isdigit():
                    numero = int(proxima["text"])
                    cabecalhos.append((numero, indice, coluna, atual["top"]))
    return cabecalhos


@dataclass(frozen=True)
class _Regiao:
    """A área de uma questão na página: número, índice da página e a caixa (x0, y0, x1, y1)."""

    numero: int
    pagina: int
    caixa: tuple[float, float, float, float]


def _regioes_por_questao(pdf: pdfplumber.PDF) -> list[_Regiao]:
    """Calcula a região de cada questão, do seu cabeçalho ao próximo cabeçalho na mesma coluna.

    Mantém só a primeira ocorrência de cada número, na mesma ordem de leitura de `_linhas_ordenadas`
    (página, coluna, top), para casar com a versão de questão que a segmentação guardou.
    """
    cabecalhos = _cabecalhos_com_coords(pdf)
    tops_por_coluna: dict[tuple[int, int], list[float]] = {}
    for _numero, pagina, coluna, top in cabecalhos:
        tops_por_coluna.setdefault((pagina, coluna), []).append(top)
    for tops in tops_por_coluna.values():
        tops.sort()

    regioes: list[_Regiao] = []
    vistos: set[int] = set()
    for numero, indice, coluna, top in sorted(cabecalhos, key=lambda c: (c[1], c[2], c[3])):
        if numero in vistos:
            continue
        vistos.add(numero)
        pagina = pdf.pages[indice]
        meio = pagina.width / 2
        x0, x1 = (0.0, meio) if coluna == 0 else (meio, pagina.width)
        seguintes = [t for t in tops_por_coluna[(indice, coluna)] if t > top + 1]
        y1 = min(seguintes) if seguintes else pagina.height - _MARGEM_BASE
        regioes.append(_Regiao(numero, indice, (x0, top, x1, y1)))
    return regioes


def _figuras_por_questao(
    pdf: pdfplumber.PDF,
) -> dict[int, tuple[int, tuple[float, float, float, float]]]:
    """Acha a figura de cada questão que tem uma. Devolve {numero: (indice_pagina, bbox)}.

    A figura pode ser uma imagem raster (foto, cartaz, pintura) ou um desenho vetorial (gráfico,
    mapa, figura geométrica). A caixa devolvida é a união das duas, recortada depois para PNG.
    """
    figuras: dict[int, tuple[int, tuple[float, float, float, float]]] = {}
    for regiao in _regioes_por_questao(pdf):
        pagina = pdf.pages[regiao.pagina]
        x0, y0, x1, y1 = regiao.caixa
        recorte = pagina.crop(
            (x0, max(y0, _MARGEM_TOPO), x1, min(y1, pagina.height - _MARGEM_BASE))
        )
        caixa = _figura_da_regiao(recorte)
        if caixa is not None:
            figuras[regiao.numero] = (regiao.pagina, caixa)
    return figuras


def _figura_da_regiao(
    recorte: pdfplumber.page.CroppedPage,
) -> tuple[float, float, float, float] | None:
    """Une a figura raster e a vetorial de uma região, se houver. Devolve a caixa ou None."""
    caixas: list[tuple[float, float, float, float]] = []
    for imagem in recorte.images:
        if (imagem["x1"] - imagem["x0"]) >= _MIN_LADO_FIGURA and (
            imagem["bottom"] - imagem["top"]
        ) >= _MIN_LADO_FIGURA:
            caixas.append((imagem["x0"], imagem["top"], imagem["x1"], imagem["bottom"]))
    vetorial = _figura_vetorial(recorte)
    if vetorial is not None:
        caixas.append(vetorial)
    if not caixas:
        return None
    return (
        min(c[0] for c in caixas),
        min(c[1] for c in caixas),
        max(c[2] for c in caixas),
        max(c[3] for c in caixas),
    )


def _figura_vetorial(
    recorte: pdfplumber.page.CroppedPage,
) -> tuple[float, float, float, float] | None:
    """Detecta um desenho vetorial na região: aglomerado de tinta grande com pouco texto dentro.

    Descarta marcadores de alternativa e ícones (pequenos), réguas finas, e molduras de caixas de
    texto e tabelas, que têm muito texto dentro da caixa. Devolve a caixa do desenho ou None.
    """
    objetos = []
    for obj in [*recorte.curves, *recorte.lines, *recorte.rects]:
        largura = obj["x1"] - obj["x0"]
        altura = obj["bottom"] - obj["top"]
        if largura < _MIN_OBJ_VETOR and altura < _MIN_OBJ_VETOR:
            continue
        if largura < _ESPESSURA_MIN or altura < _ESPESSURA_MIN:
            continue
        objetos.append(obj)
    if not objetos:
        return None

    x0 = min(o["x0"] for o in objetos)
    y0 = min(o["top"] for o in objetos)
    x1 = max(o["x1"] for o in objetos)
    y1 = max(o["bottom"] for o in objetos)
    if (x1 - x0) < _MIN_LADO_VETOR or (y1 - y0) < _MIN_LADO_VETOR:
        return None
    if _fracao_texto((x0, y0, x1, y1), recorte) > _MAX_FRACAO_TEXTO_FIGURA:
        return None
    return (x0, y0, x1, y1)


def _fracao_texto(
    caixa: tuple[float, float, float, float], recorte: pdfplumber.page.CroppedPage
) -> float:
    """Fração da área da caixa coberta por texto, para separar figura de caixa de texto e tabela."""
    x0, y0, x1, y1 = caixa
    area = (x1 - x0) * (y1 - y0)
    if area <= 0:
        return 0.0
    coberto = 0.0
    for palavra in recorte.extract_words():
        ix0 = max(x0, palavra["x0"])
        iy0 = max(y0, palavra["top"])
        ix1 = min(x1, palavra["x1"])
        iy1 = min(y1, palavra["bottom"])
        if ix1 > ix0 and iy1 > iy0:
            coberto += (ix1 - ix0) * (iy1 - iy0)
    return coberto / area


def _rasterizar_figuras(
    caminho_prova: Path,
    figuras: dict[int, tuple[int, tuple[float, float, float, float]]],
    ano: int,
    dir_figuras: Path,
) -> dict[int, list[str]]:
    """Recorta a figura de cada questão para um PNG e devolve {numero: [caminho]}."""
    dir_figuras.mkdir(parents=True, exist_ok=True)
    # Limpa PNGs de uma rodada anterior, para a saída refletir só a detecção atual.
    for antigo in dir_figuras.glob(f"enem-{ano}-*.png"):
        antigo.unlink()
    documento = pdfium.PdfDocument(str(caminho_prova))
    escala = 200 / 72  # 200 dpi
    cache_paginas: dict[int, object] = {}
    saidas: dict[int, list[str]] = {}
    try:
        for numero, (indice_pagina, bbox) in figuras.items():
            if indice_pagina not in cache_paginas:
                cache_paginas[indice_pagina] = (
                    documento[indice_pagina].render(scale=escala).to_pil()
                )
            imagem_pagina = cache_paginas[indice_pagina]
            x0, top, x1, bottom = bbox
            caixa = (
                int((x0 - _FOLGA_FIGURA) * escala),
                int((top - _FOLGA_FIGURA) * escala),
                int((x1 + _FOLGA_FIGURA) * escala),
                int((bottom + _FOLGA_FIGURA) * escala),
            )
            destino = dir_figuras / f"enem-{ano}-{numero:02d}.png"
            imagem_pagina.crop(caixa).save(destino)
            saidas[numero] = [str(destino)]
    finally:
        documento.close()
    return saidas


def carregar_prova_pdf(
    caminho_prova: str | Path,
    caminho_gabarito: str | Path,
    ano: int = 2025,
    dia: int = 1,
    lingua: str = "ingles",
    dir_figuras: str | Path | None = None,
) -> list[Questao]:
    """Carrega uma prova do ENEM a partir dos PDFs do INEP e normaliza para `Questao`.

    Lê o texto em ordem de leitura, separa as questões, casa cada uma com o gabarito e recorta as
    figuras das questões que têm imagem. As figuras vão para `dir_figuras`, por padrão
    `data/figures/<ano>/dia<dia>`.
    """
    caminho_prova = Path(caminho_prova)
    caminho_gabarito = Path(caminho_gabarito)
    if dir_figuras is None:
        dir_figuras = Path("data/figures") / str(ano) / f"dia{dia}"
    dir_figuras = Path(dir_figuras)

    with pdfplumber.open(str(caminho_gabarito)) as pdf_gab:
        linhas_gab = [
            linha
            for pagina in pdf_gab.pages
            for linha in (pagina.extract_text() or "").splitlines()
        ]
    gabarito = parse_gabarito(linhas_gab, lingua=lingua)

    with pdfplumber.open(str(caminho_prova)) as pdf:
        blocos = segmentar_questoes(_linhas_ordenadas(pdf))
        figuras = _figuras_por_questao(pdf)

    caminhos_figuras = _rasterizar_figuras(caminho_prova, figuras, ano, dir_figuras)

    questoes: list[Questao] = []
    anuladas: list[int] = []
    for bloco in blocos:
        if bloco.numero not in gabarito:
            anuladas.append(bloco.numero)  # questão anulada não tem gabarito válido
            continue
        questoes.append(
            montar_questao(
                bloco,
                gabarito,
                ano,
                tem_imagem=bloco.numero in caminhos_figuras,
                imagens=caminhos_figuras.get(bloco.numero, []),
            )
        )
    com_imagem = sum(1 for q in questoes if q.tem_imagem)
    if anuladas:
        logger.info("Puladas %d questões sem gabarito (anuladas): %s", len(anuladas), anuladas)
    logger.info(
        "Carregadas %d questões do ENEM %d dia %d (PDF), %d com imagem",
        len(questoes),
        ano,
        dia,
        com_imagem,
    )
    return questoes
