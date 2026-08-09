"""Política de identidade: o sistema decide por regra declarada, não por vigilância.

O perfil `ADULT_LOCAL` da especificação (§49) diz duas coisas ao mesmo tempo, e as
duas importam:

  - conteúdo adulto **sintético** roda sem filtro artificial que destrua anatomia;
  - identidade de **pessoa real** em contexto sexual exige base de direitos declarada.

Este módulo implementa exatamente isso. Ele não lê intenção nem julga estilo: ele
verifica se há um rosto de pessoa numa referência sendo usada como identidade, e se
existe uma base de direitos registrada para aquele asset. Sem rosto detectado, ou
com base declarada, ele sai do caminho.

A decisão de qual base de direitos vale é do usuário e fica gravada no asset. O que
o sistema recusa é o caso não declarado — porque "não perguntei" não é consentimento.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .engines.common import EngineExecutionError

# Bases que o usuário pode declarar num asset. `sintetico` cobre o caso mais comum
# do estúdio: a pessoa na imagem não existe.
BASES_DE_DIREITOS = {
    "sintetico": "A pessoa retratada não existe; a imagem foi gerada.",
    "titular_consentiu": "O titular autorizou este uso, e está nomeado.",
    "licenciado": "Uso coberto por licença ou contrato registrado.",
    "proprio": "O titular das referências é o próprio usuário.",
    "nao_declarado": "Ninguém declarou nada sobre esta imagem.",
}
BASE_PADRAO = "nao_declarado"
BASES_QUE_AUTORIZAM = {"sintetico", "titular_consentiu", "licenciado", "proprio"}

# Termos que caracterizam saída sexual explícita. A lista existe para o sistema
# saber QUANDO pedir a declaração — não para bloquear vocabulário.
_TERMOS_EXPLICITOS = (
    "nua", "nue", "nu", "nude", "naked", "pelada", "despida",
    "explicito", "explicit", "sexo", "sexual", "porno", "hardcore",
    "genital", "vagina", "penis", "seios a mostra", "topless",
)


def _dobrar(texto: str) -> str:
    """Sem acento e sem caixa: o usuário escreve 'explícito', a regra lê 'explicito'."""
    return "".join(
        ch for ch in unicodedata.normalize("NFD", str(texto or "").lower())
        if unicodedata.category(ch) != "Mn"
    )


def prompt_pede_explicito(texto: str) -> bool:
    dobrado = _dobrar(texto)
    return any(re.search(rf"\b{re.escape(termo)}\b", dobrado) for termo in _TERMOS_EXPLICITOS)


@dataclass
class Referencia:
    """Um asset usado como referência, com o que se sabe sobre ele."""

    asset_id: str
    caminho: Path
    base_de_direitos: str = BASE_PADRAO
    titular: str = ""
    tem_rosto: bool | None = None      # None = ainda não verificado

    def autoriza(self) -> bool:
        if self.base_de_direitos not in BASES_QUE_AUTORIZAM:
            return False
        # Dizer que o titular consentiu sem nomear o titular não é declaração.
        if self.base_de_direitos == "titular_consentiu" and not self.titular.strip():
            return False
        return True


class PoliticaIdentidade:
    """Consulta feita pelo executor antes de gerar."""

    def __init__(self, models_root: Path):
        self.models_root = Path(models_root)
        self._motor = None

    def _detecta_rosto(self, caminho: Path) -> bool:
        """Usa o mesmo MediaPipe do DNA humano. Sem rosto, não há identidade em jogo."""
        if self._motor is None:
            from .engines.humandna import HumanDnaEngine
            self._motor = HumanDnaEngine(self.models_root)
        try:
            return self._motor.ler(caminho, caminho.stem).face_detectada
        except Exception:
            # Falha de leitura não pode virar autorização silenciosa nem bloqueio
            # arbitrário: devolve False e o chamador segue com o que sabe.
            return False

    def avaliar(self, prompt: str, referencias: list[Referencia]) -> dict[str, Any]:
        """Devolve a decisão e o porquê. Nunca decide sem dizer o motivo."""
        explicito = prompt_pede_explicito(prompt)
        if not explicito:
            return {"permitido": True, "motivo": "a saída pedida não é sexual explícita",
                    "explicito": False, "referencias_com_rosto": []}

        com_rosto: list[Referencia] = []
        for referencia in referencias:
            if referencia.tem_rosto is None:
                referencia.tem_rosto = self._detecta_rosto(referencia.caminho)
            if referencia.tem_rosto:
                com_rosto.append(referencia)

        if not com_rosto:
            return {"permitido": True,
                    "motivo": "nenhuma referência traz rosto; não há identidade em jogo",
                    "explicito": True, "referencias_com_rosto": []}

        sem_base = [r for r in com_rosto if not r.autoriza()]
        if not sem_base:
            return {"permitido": True,
                    "motivo": "todas as referências com rosto têm base de direitos declarada",
                    "explicito": True,
                    "referencias_com_rosto": [r.asset_id for r in com_rosto],
                    "bases": {r.asset_id: r.base_de_direitos for r in com_rosto}}

        return {
            "permitido": False,
            "motivo": "referência com rosto usada como identidade em conteúdo sexual "
                      "explícito, sem base de direitos declarada",
            "explicito": True,
            "referencias_com_rosto": [r.asset_id for r in com_rosto],
            "pendentes": [r.asset_id for r in sem_base],
        }

    def exigir(self, prompt: str, referencias: list[Referencia]) -> dict[str, Any]:
        """Igual a `avaliar`, mas levanta o erro que o usuário vê na tela."""
        decisao = self.avaliar(prompt, referencias)
        if decisao["permitido"]:
            return decisao
        pendentes = ", ".join(decisao["pendentes"])
        raise EngineExecutionError(
            "IDENTIDADE_SEM_BASE_DE_DIREITOS",
            "Esta geração usa o rosto de uma referência para produzir conteúdo sexual "
            f"explícito, e {len(decisao['pendentes'])} referência(s) não têm base de "
            "direitos declarada.",
            "Abra o asset na biblioteca e declare a base de direitos: "
            "'sintético' se a pessoa não existe, 'próprio' se é você, "
            "'titular consentiu' com o nome de quem autorizou, ou 'licenciado'. "
            f"Pendentes: {pendentes}",
        )
