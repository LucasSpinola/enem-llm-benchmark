"""Montagem do prompt a partir de uma `Questao`, em texto e com imagem quando houver.

Há duas variantes. A variante com raciocínio pede que o modelo pense passo a passo e conclua com a
letra, e o raciocínio guardado alimenta os erros comentados. A variante curta pede só a letra, mais
barata para a cota gratuita. As duas terminam pedindo a resposta no formato "Resposta: X", para a
extração ficar simples e estável.
"""

from pathlib import Path

from enembench.normalizacao import LETRAS
from enembench.schema import Questao

_INSTRUCAO_RACIOCINIO = (
    "Explique seu raciocínio passo a passo e, na última linha, escreva apenas "
    '"Resposta: X", onde X é a letra da alternativa correta.'
)
_INSTRUCAO_CURTA = 'Responda apenas com a letra da alternativa correta, no formato "Resposta: X".'
_AVISO_IMAGEM = "Considere também a imagem da questão, fornecida junto deste enunciado."


def montar_prompt(questao: Questao, com_raciocinio: bool = True) -> str:
    """Monta o texto do prompt de uma questão, escolhendo a variante de instrução.

    A variante com raciocínio é o padrão do benchmark. Quando a questão tem imagem, o texto avisa o
    modelo, e os bytes da imagem vão à parte, pelo parâmetro `imagens` do provedor.
    """
    linhas = [
        "Você é um estudante resolvendo uma questão de múltipla escolha do ENEM.",
        "Leia o enunciado e escolha a única alternativa correta.",
        "",
        questao.enunciado.strip(),
        "",
    ]
    for letra in LETRAS:
        linhas.append(f"{letra}) {questao.alternativas[letra].strip()}")
    linhas.append("")
    if questao.tem_imagem:
        linhas.append(_AVISO_IMAGEM)
    linhas.append(_INSTRUCAO_RACIOCINIO if com_raciocinio else _INSTRUCAO_CURTA)
    return "\n".join(linhas)


def carregar_imagens(questao: Questao) -> list[bytes]:
    """Lê os bytes das imagens locais de uma questão, para enviar a modelos multimodais.

    Considera apenas caminhos de arquivo existentes, como os PNGs gerados pela fonte de PDF. URLs,
    da fonte Hugging Face, ficam para a etapa do runner, que baixa e cacheia. Sem imagens, devolve
    uma lista vazia.
    """
    bytes_imagens: list[bytes] = []
    for referencia in questao.imagens:
        caminho = Path(referencia)
        if caminho.is_file():
            bytes_imagens.append(caminho.read_bytes())
    return bytes_imagens
