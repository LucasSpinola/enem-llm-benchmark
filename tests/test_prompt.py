"""Testes da montagem do prompt a partir de uma `Questao`."""

from enembench.prompt import montar_prompt
from enembench.schema import Questao


def _questao(tem_imagem: bool = False) -> Questao:
    return Questao(
        id="enem-2025-07",
        ano=2025,
        area="linguagens",
        enunciado="Qual é o tema central do texto?",
        alternativas={
            "A": "a saudade",
            "B": "a viagem",
            "C": "o trabalho",
            "D": "a cidade",
            "E": "o tempo",
        },
        gabarito="E",
        tem_imagem=tem_imagem,
        imagens=[],
    )


def test_montar_prompt_inclui_enunciado_e_alternativas() -> None:
    prompt = montar_prompt(_questao())
    assert "Qual é o tema central do texto?" in prompt
    assert "A) a saudade" in prompt
    assert "E) o tempo" in prompt


def test_montar_prompt_com_raciocinio_pede_passo_a_passo() -> None:
    prompt = montar_prompt(_questao(), com_raciocinio=True)
    assert "passo a passo" in prompt
    assert "Resposta: X" in prompt


def test_montar_prompt_curto_nao_pede_raciocinio() -> None:
    prompt = montar_prompt(_questao(), com_raciocinio=False)
    assert "passo a passo" not in prompt
    assert "apenas com a letra" in prompt


def test_montar_prompt_avisa_quando_tem_imagem() -> None:
    assert "imagem" in montar_prompt(_questao(tem_imagem=True))
    assert "imagem" not in montar_prompt(_questao(tem_imagem=False))
