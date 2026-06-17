"""Testes das funções puras da fonte PDF, com fixtures sintéticas, sem abrir nenhum PDF."""

import pytest

from enembench.pdf_enem import (
    BlocoQuestao,
    extrair_alternativas,
    linha_e_ruido,
    montar_questao,
    parse_gabarito,
    segmentar_questoes,
)
from enembench.schema import AREA_HUMANAS, AREA_LINGUAGENS


def test_linha_e_ruido() -> None:
    assert linha_e_ruido("")
    assert linha_e_ruido("   ")
    assert linha_e_ruido("*010175AZ8*")
    assert linha_e_ruido("ENEM2025ENEM2025ENEM2025ENEM2025")
    assert linha_e_ruido("7")
    assert linha_e_ruido(
        "LINGUAGENS, CÓDIGOS E SUAS TECNOLOGIAS E REDAÇÃO | 1º DIA | CADERNO 1 | AZUL"
    )
    assert linha_e_ruido("CIÊNCIAS DA NATUREZA E SUAS TECNOLOGIAS | 2º DIA | CADERNO 7 | AZUL")
    assert not linha_e_ruido("A pela especialização de seu público-alvo.")
    assert not linha_e_ruido("Nesse texto, a autora defende que")


def test_segmentar_questoes_tres_digitos() -> None:
    # O Dia 2 vai de 91 a 180, com números de três dígitos.
    linhas = [
        "QUESTÃO 136",
        "Enunciado de matemática.",
        "A um",
        "B dois",
        "C tres",
        "D quatro",
        "E cinco",
    ]
    blocos = segmentar_questoes(linhas)
    assert [b.numero for b in blocos] == [136]


def test_extrair_alternativas_imagem() -> None:
    # Em algumas questões as alternativas são imagens e a linha tem só a letra.
    enunciado, alternativas = extrair_alternativas(["Veja as figuras.", "A", "B", "C", "D", "E"])
    assert enunciado == "Veja as figuras."
    assert alternativas == {"A": "", "B": "", "C": "", "D": "", "E": ""}


def test_segmentar_questoes_basico() -> None:
    linhas = [
        "QUESTÃO 06",
        "Enunciado da seis.",
        "A alfa",
        "B beta",
        "QUESTÃO 07",
        "Enunciado da sete.",
        "C gama",
    ]
    blocos = segmentar_questoes(linhas)
    assert [b.numero for b in blocos] == [6, 7]
    assert blocos[0].linhas == ["Enunciado da seis.", "A alfa", "B beta"]


def test_segmentar_questoes_dedup_lingua() -> None:
    # Questão 01 aparece duas vezes (inglês depois espanhol); fica só a primeira.
    linhas = [
        "QUESTÃO 01",
        "Versão inglês.",
        "QUESTÃO 01",
        "Versão espanhol.",
        "QUESTÃO 02",
        "Outra.",
    ]
    blocos = segmentar_questoes(linhas)
    assert [b.numero for b in blocos] == [1, 2]
    assert blocos[0].linhas == ["Versão inglês."]


def test_segmentar_questoes_pula_redacao() -> None:
    linhas = [
        "QUESTÃO 45",
        "Enunciado.",
        "A um",
        "PROPOSTA DE REDAÇÃO",
        "Texto motivador da redação.",
        "QUESTÃO 46",
        "Próxima.",
    ]
    blocos = segmentar_questoes(linhas)
    assert [b.numero for b in blocos] == [45, 46]
    assert "Texto motivador da redação." not in blocos[0].linhas


def test_extrair_alternativas_simples() -> None:
    linhas = [
        "Enunciado em uma linha.",
        "A primeira",
        "B segunda",
        "C terceira",
        "D quarta",
        "E quinta",
    ]
    enunciado, alternativas = extrair_alternativas(linhas)
    assert enunciado == "Enunciado em uma linha."
    assert alternativas == {
        "A": "primeira",
        "B": "segunda",
        "C": "terceira",
        "D": "quarta",
        "E": "quinta",
    }


def test_extrair_alternativas_multilinha() -> None:
    linhas = [
        "Parte um do enunciado.",
        "Parte dois do enunciado.",
        "A primeira",
        "B segunda que continua",
        "na linha seguinte",
        "C terceira",
        "D quarta",
        "E quinta",
    ]
    enunciado, alternativas = extrair_alternativas(linhas)
    assert enunciado == "Parte um do enunciado. Parte dois do enunciado."
    assert alternativas["B"] == "segunda que continua na linha seguinte"
    assert alternativas["E"] == "quinta"


def test_extrair_alternativas_sem_sequencia() -> None:
    with pytest.raises(ValueError):
        extrair_alternativas(["Só enunciado.", "A uma", "B duas"])


def test_parse_gabarito_uma_letra() -> None:
    linhas = ["46 E", "47 D", "90 A"]
    assert parse_gabarito(linhas) == {46: "E", 47: "D", 90: "A"}


def test_parse_gabarito_ingles_espanhol() -> None:
    # Nas questões 1 a 5 há duas letras: inglês e depois espanhol.
    linhas = ["1 D B", "2 D A", "6 E"]
    assert parse_gabarito(linhas, lingua="ingles") == {1: "D", 2: "D", 6: "E"}
    assert parse_gabarito(linhas, lingua="espanhol") == {1: "B", 2: "A", 6: "E"}


def test_parse_gabarito_varios_pares_por_linha() -> None:
    # Tabelas lado a lado podem juntar duas questões numa linha só.
    linhas = ["5 A C 50 A", "QUESTÃO GABARITO"]
    assert parse_gabarito(linhas) == {5: "A", 50: "A"}


def test_parse_gabarito_dia2() -> None:
    # No Dia 2 o pdfplumber serializa como "NÚMERO LETRA NÚMERO LETRA" (Natureza e Matemática).
    linhas = ["91 D 136 C", "92 D 137 B", "100 A 145 D"]
    assert parse_gabarito(linhas) == {91: "D", 92: "D", 100: "A", 136: "C", 137: "B", 145: "D"}


def test_parse_gabarito_anulado() -> None:
    # Questões anuladas não têm letra válida e ficam de fora do gabarito.
    assert parse_gabarito(["123 Anulado 168 D"]) == {168: "D"}


def test_montar_questao() -> None:
    bloco = BlocoQuestao(
        numero=7,
        linhas=["Enunciado.", "A um", "B dois", "C tres", "D quatro", "E cinco"],
    )
    questao = montar_questao(bloco, {7: "c"}, 2025, tem_imagem=False, imagens=[])
    assert questao.id == "enem-2025-07"
    assert questao.area == AREA_LINGUAGENS
    assert questao.gabarito == "C"
    assert questao.alternativas["D"] == "quatro"


def test_montar_questao_humanas_com_imagem() -> None:
    bloco = BlocoQuestao(
        numero=46,
        linhas=["Veja a charge.", "A um", "B dois", "C tres", "D quatro", "E cinco"],
    )
    questao = montar_questao(
        bloco, {46: "B"}, 2025, tem_imagem=True, imagens=["data/figures/2025/dia1/enem-2025-46.png"]
    )
    assert questao.area == AREA_HUMANAS
    assert questao.tem_imagem is True
    assert questao.imagens == ["data/figures/2025/dia1/enem-2025-46.png"]


def test_montar_questao_sem_gabarito() -> None:
    bloco = BlocoQuestao(
        numero=8,
        linhas=["Enunciado.", "A um", "B dois", "C tres", "D quatro", "E cinco"],
    )
    with pytest.raises(ValueError):
        montar_questao(bloco, {}, 2025, tem_imagem=False, imagens=[])
