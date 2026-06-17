"""Testes do runner com o FakeProvider, garantindo cache, pulo de imagem e formato do resultado."""

from pathlib import Path

from enembench.cache import Cache
from enembench.providers.fake import FakeProvider
from enembench.runner import (
    ModeloConfig,
    carregar_modelos,
    executar_modelo,
    salvar_resultados_csv,
)
from enembench.schema import Questao


def _questao(qid: str, tem_imagem: bool = False, gabarito: str = "B") -> Questao:
    return Questao(
        id=qid,
        ano=2025,
        area="linguagens",
        enunciado="enunciado",
        alternativas={letra: letra for letra in "ABCDE"},
        gabarito=gabarito,
        tem_imagem=tem_imagem,
        imagens=["nao_existe.png"] if tem_imagem else [],
    )


def test_carregar_modelos(tmp_path: Path) -> None:
    caminho = tmp_path / "models.yaml"
    caminho.write_text(
        "- id: gemini-flash\n"
        "  provider: gemini\n"
        "  model: gemini-2.0-flash\n"
        "  multimodal: true\n"
        "- id: llama-70b\n"
        "  provider: groq\n"
        "  model: llama-3.3-70b-versatile\n"
        "  multimodal: false\n",
        encoding="utf-8",
    )
    modelos = carregar_modelos(caminho)
    assert [m.id for m in modelos] == ["gemini-flash", "llama-70b"]
    assert modelos[0].multimodal is True
    assert modelos[1].multimodal is False


def test_modelo_de_texto_pula_imagem(tmp_path: Path) -> None:
    config = ModeloConfig("llama", "groq", "x", multimodal=False)
    provedor = FakeProvider(resposta="Resposta: B")
    questoes = [_questao("q-texto"), _questao("q-img", tem_imagem=True)]

    resultados = executar_modelo(config, provedor, questoes, Cache(tmp_path))

    assert [r.questao_id for r in resultados] == ["q-texto"]
    assert len(provedor.chamadas) == 1


def test_cache_evita_segunda_chamada(tmp_path: Path) -> None:
    config = ModeloConfig("fake-m", "fake", "fake", multimodal=False)
    provedor = FakeProvider(resposta="Resposta: B")
    questoes = [_questao("q1"), _questao("q2")]
    cache = Cache(tmp_path)

    primeiros = executar_modelo(config, provedor, questoes, cache)
    segundos = executar_modelo(config, provedor, questoes, cache)

    assert len(provedor.chamadas) == 2  # só na primeira passada
    assert all(r.acertou for r in primeiros)  # gabarito B, resposta B
    assert len(segundos) == 2


class _ProvedorQueFalha:
    """Provedor de teste que sempre lança erro, simulando cota esgotada ou falha de rede."""

    def responder(self, prompt: str, imagens: list[bytes] | None = None) -> str:
        raise RuntimeError("falha simulada")


def test_falha_em_questao_nao_derruba_run(tmp_path: Path) -> None:
    config = ModeloConfig("m", "fake", "fake", multimodal=False)
    questoes = [_questao("q1"), _questao("q2")]

    resultados = executar_modelo(config, _ProvedorQueFalha(), questoes, Cache(tmp_path))

    assert len(resultados) == 2
    assert all(r.alternativa is None and not r.acertou for r in resultados)


def test_formato_do_resultado(tmp_path: Path) -> None:
    config = ModeloConfig("fake-m", "fake", "fake", multimodal=False)
    provedor = FakeProvider(resposta="Penso um pouco. Resposta: C")

    resultados = executar_modelo(config, provedor, [_questao("q1", gabarito="C")], Cache(tmp_path))

    resultado = resultados[0]
    assert resultado.modelo == "fake-m"
    assert resultado.alternativa == "C"
    assert resultado.acertou is True
    assert resultado.area == "linguagens"


def test_salvar_resultados_csv(tmp_path: Path) -> None:
    config = ModeloConfig("fake-m", "fake", "fake", multimodal=False)
    provedor = FakeProvider(resposta="Resposta: B")
    resultados = executar_modelo(config, provedor, [_questao("q1")], Cache(tmp_path))

    saida = tmp_path / "out.csv"
    salvar_resultados_csv(resultados, saida)

    linhas = saida.read_text(encoding="utf-8").splitlines()
    assert linhas[0].startswith("questao_id,modelo,ano,area")
    assert linhas[1].startswith("q1,fake-m,2025,linguagens")
