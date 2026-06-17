"""Testes do cache em disco das respostas dos modelos."""

from pathlib import Path

from enembench.cache import Cache


def test_cache_ida_e_volta(tmp_path: Path) -> None:
    cache = Cache(tmp_path)
    assert cache.obter("m1", "q1", "prompt") is None
    cache.guardar("m1", "q1", "prompt", "Resposta: C", 1.5)
    assert cache.obter("m1", "q1", "prompt") == "Resposta: C"


def test_cache_invalida_quando_prompt_muda(tmp_path: Path) -> None:
    cache = Cache(tmp_path)
    cache.guardar("m1", "q1", "prompt antigo", "Resposta: A", 1.0)
    assert cache.obter("m1", "q1", "prompt novo") is None


def test_cache_considera_imagens(tmp_path: Path) -> None:
    cache = Cache(tmp_path)
    cache.guardar("m1", "q1", "p", "Resposta: A", 1.0, imagens=[b"img"])
    assert cache.obter("m1", "q1", "p", imagens=[b"img"]) == "Resposta: A"
    assert cache.obter("m1", "q1", "p", imagens=[b"outra"]) is None
    assert cache.obter("m1", "q1", "p") is None  # sem imagem é diferente de com imagem


def test_cache_aceita_nomes_com_barra(tmp_path: Path) -> None:
    cache = Cache(tmp_path)
    cache.guardar("meta-llama/foo:free", "enem-2025-01", "p", "Resposta: D", 0.1)
    assert cache.obter("meta-llama/foo:free", "enem-2025-01", "p") == "Resposta: D"
