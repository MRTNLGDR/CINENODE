"""Módulos de entrega com gates e evidência — o alerta de conclusão do plano.

A governança que já existe rastreia *tarefas*. Isto rastreia *módulos*: um conjunto
de nós e fluxos que só é declarado concluído quando cada portão passa com evidência
executável anexada.

A regra que dá valor ao alerta é negativa: nenhum módulo fica `CONCLUIDO` enquanto
houver gate desconhecido, evidência ausente, ou nó que ainda é só especificação.
Um alerta que sempre acende não informa nada.
"""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .util import utc_now

ESTADOS = ("CONCLUIDO", "EM_PROGRESSO", "BLOQUEADO", "REGREDIU", "PARCIAL")
GATE_STATUS = ("PASS", "FAIL", "BLOCKED", "UNKNOWN")


@dataclass
class Gate:
    id: str
    label: str
    rule: str
    command: str
    evidence: str
    status: str = "UNKNOWN"
    detail: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "rotulo": self.label, "regra": self.rule,
            "comando": self.command, "evidencia": self.evidence,
            "status": self.status, "detalhe": self.detail,
        }


@dataclass
class Modulo:
    id: str
    titulo: str
    icone: str
    fase: str
    depende_de: list[str] = field(default_factory=list)
    nos: list[str] = field(default_factory=list)
    fluxos: list[str] = field(default_factory=list)
    gates: list[Gate] = field(default_factory=list)
    bloqueio: str = ""

    # ---- avaliação ------------------------------------------------------

    def estado(self, catalogo_tipos: set[str]) -> str:
        """O estado sai dos gates e do catálogo real, nunca de um campo escrito à mão."""
        if self.bloqueio:
            return "BLOQUEADO"
        if any(gate.status == "BLOCKED" for gate in self.gates):
            return "BLOQUEADO"
        if any(gate.status == "FAIL" for gate in self.gates):
            # Falhar depois de já ter passado é regressão, não "em progresso".
            return "REGREDIU" if self.progresso(catalogo_tipos) >= 99 else "EM_PROGRESSO"
        faltando = self.nos_faltando(catalogo_tipos)
        if all(gate.status == "PASS" for gate in self.gates) and self.gates and not faltando:
            return "CONCLUIDO"
        if any(gate.status == "PASS" for gate in self.gates):
            return "EM_PROGRESSO"
        return "PARCIAL"

    def nos_faltando(self, catalogo_tipos: set[str]) -> list[str]:
        """Nó prometido que não existe no catálogo é promessa, não entrega."""
        return [tipo for tipo in self.nos if tipo not in catalogo_tipos]

    def progresso(self, catalogo_tipos: set[str]) -> int:
        """Metade do peso nos gates, metade nos nós que realmente existem."""
        peso_gates = 0.0
        if self.gates:
            peso_gates = sum(1 for g in self.gates if g.status == "PASS") / len(self.gates)
        peso_nos = 1.0
        if self.nos:
            peso_nos = sum(1 for tipo in self.nos if tipo in catalogo_tipos) / len(self.nos)
        return int(round((peso_gates * 0.5 + peso_nos * 0.5) * 100))

    def as_dict(self, catalogo_tipos: set[str]) -> dict[str, Any]:
        faltando = self.nos_faltando(catalogo_tipos)
        return {
            "id": self.id,
            "titulo": self.titulo,
            "icone": self.icone,
            "fase": self.fase,
            "depende_de": self.depende_de,
            "estado": self.estado(catalogo_tipos),
            "progresso": self.progresso(catalogo_tipos),
            "gates": [gate.as_dict() for gate in self.gates],
            "gates_ok": sum(1 for g in self.gates if g.status == "PASS"),
            "gates_total": len(self.gates),
            "nos": self.nos,
            "nos_entregues": [tipo for tipo in self.nos if tipo in catalogo_tipos],
            "nos_faltando": faltando,
            "fluxos": self.fluxos,
            "bloqueio": self.bloqueio,
        }


def _gate(id_: str, label: str, rule: str, command: str, evidence: str) -> Gate:
    return Gate(id=id_, label=label, rule=rule, command=command, evidence=evidence)


# Gates comuns. Repetir a definição em cada módulo convidaria à divergência.
# `pytest` cru depende do PATH do shell, que no subprocess não tem o venv. Chamar
# pelo interpretador que está rodando é a única forma de acertar o ambiente sempre.
PY_EXE = "\"" + sys.executable + "\""


def gates_padrao(modulo: str) -> list[Gate]:
    return [
        _gate("GATE-FUNC", "FUNCIONA",
              "todo nó declarado está no catálogo, tem portas, campos visuais e executor",
              f"{PY_EXE} scripts/verify_module.py {modulo}",
              f"docs/evidence/{modulo}/execucao.json"),
        _gate("GATE-TEST", "TESTADO", "suíte verde, sem skip silencioso",
              f"{PY_EXE} -m pytest -q", f"docs/evidence/{modulo}/pytest.json"),
        _gate("GATE-UI", "VISUAL", "todo campo tem controle visual e todo nó tem rótulo",
              f"{PY_EXE} -m pytest tests/test_catalog_visual_rule.py -q",
              f"docs/evidence/{modulo}/ui.json"),
        _gate("GATE-PKG", "EMPACOTADO", "instala limpo, sem BOM, versão coerente",
              f"{PY_EXE} -m pytest tests/test_empacotamento.py -q",
              f"docs/evidence/{modulo}/pacote.json"),
    ]



def gates_com_licenca(modulo: str, *slots: str) -> list[Gate]:
    """Para módulo que carrega peso de terceiro.

    Um produto MIT que executa peso de licença desconhecida distribui um risco que
    não declarou. Este gate não pede que a licença seja permissiva — pede que ela
    seja conhecida. Enquanto houver peso carregável sem origem declarada, o módulo
    não é concluído, por mais que o código funcione.

    Os `slots` limitam o exame ao que o módulo realmente carrega. Sem esse recorte,
    uma pendência de licença em 3D reprovaria o módulo de vídeo — e um gate que
    acusa quem não tem culpa é um gate que o time aprende a ignorar.
    """
    escopo = ",".join(slots)
    return gates_padrao(modulo) + [
        _gate("GATE-LICENSE", "LICENCIADO",
              f"todo peso de {escopo or 'qualquer slot'} tem origem, licença e uso declarados",
              f"{PY_EXE} scripts/verify_licenses.py --evidencia "
              f"--modulo {modulo} --slots {escopo}",
              f"docs/evidence/licencas/{modulo}.json"),
    ]


def gates_perzon(modulo: str) -> list[Gate]:
    """Fase E vive no PERZON, um repositório separado.

    O gate lê o catálogo dele e repete o que ele diz de si mesmo. Rodar a suíte
    deste projeto não provaria nada sobre a implementação de lá.
    """
    return [
        _gate("GATE-SPEC", "ESPECIFICADO",
              "os microitens do workspace existem no catálogo do PERZON",
              f"{PY_EXE} scripts/verify_perzon.py {modulo}",
              f"docs/evidence/{modulo}/perzon.json"),
        _gate("GATE-TEST", "TESTADO", "suíte deste projeto verde",
              f"{PY_EXE} -m pytest -q", f"docs/evidence/{modulo}/pytest.json"),
    ]


# Roadmap executável. A fonte é esta tabela; o documento a descreve, não a substitui.
MODULOS: list[Modulo] = [
    Modulo("M-01", "CONTRATOS E GRAFO", "fluxo", "A",
           nos=["input.text", "input.asset", "output.preview"],
           gates=gates_padrao("M-01")),
    Modulo("M-02", "CANVAS E PORTAS", "roteador", "A", depende_de=["M-01"],
           gates=gates_padrao("M-02")),
    Modulo("M-03", "MANIFESTO E TUTORIAL", "conhecimento", "A", depende_de=["M-01"],
           gates=gates_padrao("M-03")),
    Modulo("M-04", "REGISTRO DE ASSETS", "memoria", "A", depende_de=["M-01"],
           gates=gates_padrao("M-04")),
    Modulo("M-05", "REGISTRO DE MODELOS", "processador", "A", depende_de=["M-01"],
           gates=gates_padrao("M-05")),
    Modulo("M-06", "JOBS E AGENDADOR", "pendente", "A", depende_de=["M-01"],
           gates=gates_padrao("M-06")),
    Modulo("M-07", "MEGA ROTEADOR", "roteador", "A", depende_de=["M-05", "M-06"],
           gates=gates_padrao("M-07")),
    Modulo("M-08", "ADAPTER COMFY", "processador", "A", depende_de=["M-01"],
           nos=["model3d.generate"], gates=gates_com_licenca("M-08", "model3d,runtime.media_graph")),
    Modulo("M-09", "ALERTA DE CONCLUSÃO", "concluido", "A", depende_de=["M-01"],
           gates=gates_padrao("M-09")),

    Modulo("M-10", "IMAGEM", "imagem", "B", depende_de=["M-07"],
           nos=["image.generate", "image.upscale", "image.resize"],
           fluxos=["IMAGEM MASTER 4K"], gates=gates_com_licenca("M-10", "image,upscale.image")),
    Modulo("M-11", "CONTROLE VISUAL", "profundidade", "B", depende_de=["M-07"],
           nos=["vision.segment", "vision.depth", "vision.pose2d"],
           bloqueio="nenhum destes nós existe ainda; depende de vendorizar SAM2, "
                    "Depth Anything e DWPose no ComfyUI",
           gates=gates_padrao("M-11")),
    Modulo("M-14", "VÍDEO", "video", "B", depende_de=["M-07"],
           nos=["video.generate", "video.trim", "video.concat"],
           fluxos=["START TO END VIDEO 4K"], gates=gates_com_licenca("M-14", "video,media.transform")),
    Modulo("M-16", "PÓS E RESTAURAÇÃO", "progresso", "B", depende_de=["M-14"],
           nos=["video.upscale", "video.interpolate", "media.filmlook"], gates=gates_com_licenca("M-16", "video,upscale.image,media.transform")),
    Modulo("M-17", "COR E VFX", "cor", "B", depende_de=["M-16"],
           nos=["media.scopes"], gates=gates_padrao("M-17")),
    Modulo("M-18", "ÁUDIO DE FILME", "audio", "B", depende_de=["M-14"],
           nos=["audio.extract", "audio.mux"], gates=gates_padrao("M-18")),
    Modulo("M-19", "MASTER FINAL", "saida", "B", depende_de=["M-17", "M-18"],
           nos=["media.export"], gates=gates_padrao("M-19")),

    Modulo("M-20", "GERAÇÃO 3D", "malha3d", "C", depende_de=["M-07"],
           nos=["model3d.generate"], gates=gates_com_licenca("M-20", "model3d")),
    Modulo("M-22", "TOPOLOGIA E UV", "malha3d", "C", depende_de=["M-20"],
           nos=["model3d.retopology"], gates=gates_com_licenca("M-22", "model3d")),
    Modulo("M-23", "TEXTURA E PBR", "cor", "C", depende_de=["M-22"],
           nos=["model3d.texture"], gates=gates_com_licenca("M-23", "model3d")),
    Modulo("M-25", "EXPORTAÇÃO 3D", "saida", "C", depende_de=["M-23"],
           nos=["model3d.export", "model3d.animate"], gates=gates_padrao("M-25")),

    Modulo("M-41", "WORKER LOCAL", "agente", "F", depende_de=["M-01"],
           nos=["llm.enhance"], gates=gates_com_licenca("M-41", "llm,visao,embed,runtime.llm")),
    Modulo("M-42", "PROMPT COMPILER", "texto", "F", depende_de=["M-41"],
           nos=["text.concat"], gates=gates_padrao("M-42")),
    Modulo("M-43", "GATEWAY DE PROVEDORES", "remoto", "F", depende_de=["M-06"],
           gates=gates_padrao("M-43")),
    Modulo("M-44", "INDEXADOR E BIBLIOTECA", "conhecimento", "F", depende_de=["M-43"],
           gates=gates_padrao("M-44")),

    # ---- FASE E: PERZON / Character OS ------------------------------------
    # Especificação executável em repositório próprio. Nenhum destes módulos pode
    # ficar CONCLUIDO enquanto o catálogo do PERZON disser specified_not_implemented.
    # A medida saiu do papel: `human.dna` roda MediaPipe local e produz proporções
    # reais. O que continua sendo especificação é malha, textura e rig — por isso o
    # módulo é PARCIAL com o escopo restante nomeado, não CONCLUIDO nem BLOQUEADO.
    Modulo("M-34", "DNA HUMANO", "personagem", "E", depende_de=["M-20"],
           nos=["human.dna"],
           bloqueio="medida facial e corporal implementada e testada; malha 3D, "
                    "textura e rig seguem no PERZON como specified_not_implemented",
           gates=[
               _gate("GATE-FUNC", "FUNCIONA",
                     "o nó human.dna está no catálogo, tem portas, campos visuais e executor",
                     f"{PY_EXE} scripts/verify_module.py M-34",
                     "docs/evidence/M-34/execucao.json"),
               _gate("GATE-MEDIDA", "MEDIDO",
                     "a geometria das medidas está correta e testada",
                     f"{PY_EXE} -m pytest tests/test_humandna.py -q",
                     "docs/evidence/M-34/medida.json"),
               _gate("GATE-SPEC", "ESPECIFICADO",
                     "os microitens do workspace existem no catálogo do PERZON",
                     f"{PY_EXE} scripts/verify_perzon.py M-34",
                     "docs/evidence/M-34/perzon.json"),
               _gate("GATE-TEST", "TESTADO", "suíte deste projeto verde",
                     f"{PY_EXE} -m pytest -q", "docs/evidence/M-34/pytest.json"),
           ]),
    Modulo("M-35", "SUPERFÍCIE HUMANA", "cor", "E", depende_de=["M-34"],
           bloqueio="PERZON: material, mesh e sculpt ainda sem algoritmo implementado",
           gates=gates_perzon("M-35")),
    Modulo("M-36", "RIG E FACE", "personagem", "E", depende_de=["M-35"],
           bloqueio="PERZON: workspace rig ainda sem algoritmo implementado",
           gates=gates_perzon("M-36")),
    Modulo("M-37", "MOCAP E MOVIMENTO", "movimento", "E", depende_de=["M-36"],
           bloqueio="PERZON: workspace motion ainda sem algoritmo implementado",
           gates=gates_perzon("M-37")),
    Modulo("M-38", "CABELO E VESTUÁRIO", "personagem", "E", depende_de=["M-35"],
           bloqueio="PERZON: hair e garment ainda sem algoritmo implementado",
           gates=gates_perzon("M-38")),
    Modulo("M-39", "VOZ DO PERSONAGEM", "audio", "E", depende_de=["M-36"],
           bloqueio="PERZON: workspace voice ainda sem algoritmo implementado",
           gates=gates_perzon("M-39")),
    Modulo("M-40", "ENTREGA DE PERSONAGEM", "saida", "E", depende_de=["M-36", "M-38"],
           bloqueio="PERZON: formats, connectors e game ainda sem algoritmo implementado",
           gates=gates_perzon("M-40")),

    Modulo("M-52", "EMPACOTAMENTO", "processador", "G",
           gates=gates_padrao("M-52")),
]

FASES = {
    "A": "FUNDAÇÃO",
    "B": "IMAGEM E VÍDEO",
    "C": "3D E ASSETS",
    "D": "ESPACIAL, CAD, BIM E GIS",
    "E": "SERES E MOVIMENTO",
    "F": "INTELIGÊNCIA",
    "G": "PRODUTO E GOVERNANÇA",
}


class ModuleRegistry:
    """Avalia os módulos contra o disco. Nenhum estado é lido de um campo escrito à mão."""

    def __init__(self, raiz: Path, catalogo: list[dict[str, Any]]):
        self.raiz = raiz
        self.catalogo_tipos = {item["type"] for item in catalogo}

    def _avaliar_gate(self, gate: Gate, executar: bool) -> None:
        """Evidência ausente é `UNKNOWN`, nunca `PASS`. Só o arquivo prova."""
        caminho = self.raiz / gate.evidence
        if not caminho.exists():
            gate.status = "UNKNOWN"
            gate.detail = "evidência ausente"
            if not executar:
                return
            # Sem evidência gravada, o comando é a única forma de saber.
            gate.status, gate.detail = self._rodar(gate)
            return
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            gate.status = "UNKNOWN"
            gate.detail = f"evidência ilegível: {type(exc).__name__}"
            return
        status = str(dados.get("status", "UNKNOWN")).upper()
        gate.status = status if status in GATE_STATUS else "UNKNOWN"
        gate.detail = str(dados.get("summary", ""))[:160]

    def _rodar(self, gate: Gate) -> tuple[str, str]:
        try:
            processo = subprocess.run(
                gate.command, shell=True, cwd=self.raiz,
                capture_output=True, text=True, timeout=600,
            )
        except subprocess.TimeoutExpired:
            return "FAIL", "o comando estourou 600 s"
        except OSError as exc:
            return "UNKNOWN", f"não consegui executar: {exc}"
        saida = (processo.stdout or "") + (processo.stderr or "")
        cauda = [linha for linha in saida.strip().splitlines() if linha.strip()]
        return ("PASS" if processo.returncode == 0 else "FAIL",
                (cauda[-1] if cauda else "")[:160])

    def avaliar(self, *, executar: bool = False, apenas: str | None = None) -> list[Modulo]:
        modulos = [m for m in MODULOS if not apenas or m.id == apenas]
        for modulo in modulos:
            for gate in modulo.gates:
                self._avaliar_gate(gate, executar)
        return modulos

    def relatorio(self, *, executar: bool = False) -> dict[str, Any]:
        modulos = self.avaliar(executar=executar)
        itens = [m.as_dict(self.catalogo_tipos) for m in modulos]
        por_fase: dict[str, dict[str, Any]] = {}
        for fase, titulo in FASES.items():
            da_fase = [i for i in itens if i["fase"] == fase]
            if not da_fase:
                continue
            concluidos = [i for i in da_fase if i["estado"] == "CONCLUIDO"]
            por_fase[fase] = {
                "titulo": titulo,
                "modulos": len(da_fase),
                "concluidos": len(concluidos),
                "progresso": int(round(sum(i["progresso"] for i in da_fase) / len(da_fase))),
                "completa": len(concluidos) == len(da_fase),
            }
        concluidos = [i for i in itens if i["estado"] == "CONCLUIDO"]
        return {
            "modulos": itens,
            "fases": por_fase,
            "total": len(itens),
            "concluidos": len(concluidos),
            "progresso_geral": int(round(sum(i["progresso"] for i in itens) / len(itens))) if itens else 0,
            "gerado_em": utc_now(),
            "catalogo_tipos": sorted(self.catalogo_tipos),
        }

    def gravar_evidencia(self, modulo_id: str, gate_id: str, status: str, resumo: str,
                         extra: dict[str, Any] | None = None) -> Path:
        """Grava a evidência no caminho declarado pelo gate. É isto que faz o alerta acender."""
        modulo = next((m for m in MODULOS if m.id == modulo_id), None)
        if not modulo:
            raise ValueError(f"módulo desconhecido: {modulo_id}")
        gate = next((g for g in modulo.gates if g.id == gate_id), None)
        if not gate:
            raise ValueError(f"gate desconhecido: {gate_id}")
        caminho = self.raiz / gate.evidence
        caminho.parent.mkdir(parents=True, exist_ok=True)
        conteudo = {
            "gate_id": gate_id,
            "module_id": modulo_id,
            "status": status,
            "summary": resumo,
            "command": gate.command,
            "recorded_at": utc_now(),
            **(extra or {}),
        }
        caminho.write_text(json.dumps(conteudo, ensure_ascii=False, indent=2), encoding="utf-8")
        return caminho
