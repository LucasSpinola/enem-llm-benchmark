"""Cache em disco das respostas dos modelos, para não gastar cota repetindo chamadas.

Cada resposta vira um arquivo JSON em `cache/<modelo>/<questao>.json`, fácil de inspecionar e de
versionar com cuidado. A chave de validade é o hash do prompt mais as imagens, então, se o prompt
muda, o cache antigo é ignorado e a chamada refeita. Isso poupa cota e torna os resultados estáveis.
"""

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


def _hash_prompt(prompt: str, imagens: list[bytes] | None) -> str:
    """Calcula um hash curto e estável do prompt e das imagens enviadas."""
    digest = hashlib.sha256(prompt.encode("utf-8"))
    for imagem in imagens or []:
        digest.update(b"\x00")
        digest.update(hashlib.sha256(imagem).digest())
    return digest.hexdigest()[:16]


def _slug(texto: str) -> str:
    """Transforma um identificador em um nome de arquivo seguro."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", texto)


@dataclass(frozen=True)
class Cache:
    """Cache em disco com um arquivo JSON por par modelo e questão."""

    raiz: Path

    def _caminho(self, modelo: str, questao_id: str) -> Path:
        return self.raiz / _slug(modelo) / f"{_slug(questao_id)}.json"

    def obter(
        self, modelo: str, questao_id: str, prompt: str, imagens: list[bytes] | None = None
    ) -> str | None:
        """Devolve a resposta crua em cache, ou None se não houver ou se o prompt mudou."""
        caminho = self._caminho(modelo, questao_id)
        if not caminho.is_file():
            return None
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        if dados.get("hash_prompt") != _hash_prompt(prompt, imagens):
            return None
        return dados["resposta_crua"]

    def guardar(
        self,
        modelo: str,
        questao_id: str,
        prompt: str,
        resposta_crua: str,
        latencia_s: float,
        imagens: list[bytes] | None = None,
    ) -> None:
        """Grava a resposta crua de um modelo a uma questão no cache."""
        caminho = self._caminho(modelo, questao_id)
        caminho.parent.mkdir(parents=True, exist_ok=True)
        dados = {
            "modelo": modelo,
            "questao_id": questao_id,
            "hash_prompt": _hash_prompt(prompt, imagens),
            "resposta_crua": resposta_crua,
            "latencia_s": latencia_s,
        }
        caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
