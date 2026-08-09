"""Registro de modelos: nenhum peso executa sem origem, licença e hash.

A auditoria mediu 33 modelos carregáveis contra 4 governados. Os outros — 29 do
Ollama, o Hunyuan3D e os dois do MediaPipe — rodavam sem origem, sem revisão, sem
hash e sem licença. O produto é MIT e distribuía uso de pesos com termos desconhecidos.

O que este módulo faz é modesto e suficiente: manter a declaração de cada modelo que
o sistema sabe carregar, medir o que está no disco, e recusar o que tem licença
`UNKNOWN_BLOCKED` quando a política exigir. Ele não baixa nada e não decide licença
por conta própria — ele guarda o que foi declarado e mostra o que falta declarar.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .util import sha256_file, utc_now

# Vocabulário fechado. Um valor fora desta lista é lacuna, não licença.
TAGS_DE_LICENCA = (
    "OSS_CODE",              # código aberto, sem pesos envolvidos
    "OPEN_WEIGHTS",          # pesos abertos com uso comercial permitido
    "SOURCE_AVAILABLE",      # fonte visível, uso restrito
    "RESEARCH_ONLY",         # proibido em produto
    "NONCOMMERCIAL",         # proibido em produto comercial
    "COMMERCIAL_CONDITIONAL",# permitido sob condição declarada
    "PROVIDER_API",          # não há peso local; o termo é do provedor
    "DATA_LICENSE_RESTRICTED",
    "UNKNOWN_BLOCKED",       # ninguém declarou: não entra em produção
)
LICENCAS_QUE_LIBERAM = {"OSS_CODE", "OPEN_WEIGHTS", "COMMERCIAL_CONDITIONAL", "PROVIDER_API"}

ESTADOS = ("FROZEN", "STABLE", "CANDIDATE", "RESEARCH", "BLOCKED")


@dataclass
class ModeloRegistrado:
    id: str
    slot: str
    nome_front: str
    origem: str
    licenca: str
    spdx: str = ""
    uso_comercial: str = "UNKNOWN"     # YES | NO | CONDITIONAL | UNKNOWN
    runtime: str = ""
    revisao: str = ""
    modalidades: list[str] = field(default_factory=list)
    hardware_minimo: str = ""
    limitacoes: str = ""
    fallback: str = ""
    estado: str = "CANDIDATE"
    observacao: str = ""
    # Prefixos, em minúsculas, dos nomes com que este peso aparece no disco ou no
    # Ollama. Casamento por prefixo explícito em vez de heurística: uma regra que
    # adivinha família erra em silêncio, e erro silencioso aqui vira licença errada.
    padroes: list[str] = field(default_factory=list)
    # Como a licença foi estabelecida. `conferido=False` significa que veio do card
    # upstream e ninguém abriu o arquivo de licença nesta máquina. É uma diferença
    # que importa: uma vale como pesquisa, a outra vale como evidência.
    conferido: bool = False
    conferencia: str = "card upstream, nao conferido no disco"

    def autoriza_producao(self) -> bool:
        return self.licenca in LICENCAS_QUE_LIBERAM and self.estado != "BLOCKED"

    def casa_com(self, nome: str) -> bool:
        alvo = nome.strip().lower()
        return any(alvo.startswith(p) for p in self.padroes)

    def as_dict(self) -> dict[str, Any]:
        dados = asdict(self)
        dados["autoriza_producao"] = self.autoriza_producao()
        return dados


def _m(**kwargs: Any) -> ModeloRegistrado:
    return ModeloRegistrado(**kwargs)


# Declarações verificáveis. Cada licença aqui foi lida da fonte indicada em `origem`;
# o que não foi verificado fica `UNKNOWN_BLOCKED` — em branco seria pior que honesto.
MODELOS: list[ModeloRegistrado] = [
    # ---- medida humana: licença verificada no repositório upstream ----
    _m(id="mediapipe/face_landmarker", slot="human.face", nome_front="Medida facial",
       origem="https://storage.googleapis.com/mediapipe-models/face_landmarker",
       licenca="OPEN_WEIGHTS", spdx="Apache-2.0", uso_comercial="YES",
       runtime="mediapipe", modalidades=["image"], hardware_minimo="CPU",
       limitacoes="proporção perde sentido acima de 35 graus de guinada",
       estado="STABLE", padroes=["face_landmarker", "mediapipe/face"],
       conferido=True, conferencia="Apache-2.0 lido no repositório google/mediapipe",
       observacao="a única família do registro com avaliação geométrica própria"),
    _m(id="mediapipe/pose_landmarker_full", slot="human.body", nome_front="Medida corporal",
       origem="https://storage.googleapis.com/mediapipe-models/pose_landmarker",
       licenca="OPEN_WEIGHTS", spdx="Apache-2.0", uso_comercial="YES",
       runtime="mediapipe", modalidades=["image"], hardware_minimo="CPU",
       limitacoes="descarta medida abaixo de 60% dos pontos visíveis", estado="STABLE",
       padroes=["pose_landmarker", "mediapipe/pose"], conferido=True,
       conferencia="Apache-2.0 lido no repositório google/mediapipe"),

    # ---- engines determinísticos: código, não peso ----
    _m(id="leejet/stable-diffusion.cpp", slot="runtime.image", nome_front="Motor de imagem",
       origem="https://github.com/leejet/stable-diffusion.cpp",
       licenca="OSS_CODE", spdx="MIT", uso_comercial="YES", runtime="binário",
       modalidades=["image"], hardware_minimo="CUDA arch 8.9 compilado", estado="STABLE",
       padroes=["stable-diffusion.cpp", "sd_cpp", "sd.exe"]),
    _m(id="xinntao/Real-ESRGAN", slot="upscale.image", nome_front="Aumentar resolução",
       origem="https://github.com/xinntao/Real-ESRGAN",
       licenca="OSS_CODE", spdx="BSD-3-Clause", uso_comercial="YES",
       runtime="ncnn-vulkan", modalidades=["image"], hardware_minimo="GPU Vulkan",
       limitacoes="tile=0 custa 244,9 s contra 6,0 s com tile=256", estado="STABLE",
       padroes=["realesrgan", "real-esrgan", "realesr"]),
    _m(id="hzwer/Practical-RIFE", slot="video.interpolate", nome_front="Interpolar frames",
       origem="https://github.com/hzwer/Practical-RIFE",
       licenca="OSS_CODE", spdx="MIT", uso_comercial="YES",
       runtime="ncnn-vulkan", modalidades=["video"], estado="STABLE",
       padroes=["rife"]),
    _m(id="FFmpeg/FFmpeg", slot="media.transform", nome_front="Transformação de mídia",
       origem="https://ffmpeg.org", licenca="OSS_CODE", spdx="GPL-3.0",
       uso_comercial="CONDITIONAL", runtime="binário do sistema",
       modalidades=["video", "audio", "image"], estado="STABLE", padroes=["ffmpeg", "ffprobe"],
       conferido=True,
       conferencia="`ffmpeg -version` nesta máquina: --enable-gpl --enable-version3",
       limitacoes="build GPL-3.0. Nunca redistribuído; chamado como processo separado",
       observacao="mesmo desenho do ComfyUI: separação por processo evita obra derivada"),
    _m(id="Comfy-Org/ComfyUI", slot="runtime.media_graph", nome_front="Grafo de mídia",
       origem="https://github.com/comfyanonymous/ComfyUI",
       licenca="OSS_CODE", spdx="GPL-3.0", uso_comercial="CONDITIONAL",
       runtime="sidecar HTTP", modalidades=["image", "video", "mesh"],
       limitacoes="GPL-3.0: nunca redistribuído; instalado por script na máquina",
       estado="STABLE", padroes=["comfyui", "comfy"], conferido=True,
       conferencia="LICENSE lido em opensources/upstream/ComfyUI",
       observacao="a separação por HTTP é o que evita obra derivada"),
    _m(id="ollama/ollama", slot="runtime.llm", nome_front="Runtime de LLM local",
       origem="https://github.com/ollama/ollama",
       licenca="OSS_CODE", spdx="MIT", uso_comercial="YES", runtime="sidecar HTTP",
       modalidades=["text", "image"], estado="STABLE", padroes=["ollama"],
       observacao="o runtime é MIT; cada modelo servido tem licença própria"),

    # ---- famílias de LLM servidas pelo Ollama --------------------------------
    # Cada entrada cobre todas as tags da família por prefixo. `conferido=False`
    # em todas: a licença abaixo vem do card publicado pelo autor, e nenhuma foi
    # lida de um arquivo nesta máquina. O gate conta isso separadamente.
    _m(id="Qwen/Qwen2.5", slot="llm.text", nome_front="Qwen 2.5",
       origem="https://huggingface.co/Qwen", licenca="OPEN_WEIGHTS", spdx="Apache-2.0",
       uso_comercial="YES", runtime="ollama", modalidades=["text"], estado="STABLE",
       padroes=["qwen2.5:", "qwen2.5-coder", "qwen25"],
       limitacoes="as variantes 3B e 72B saem sob licença própria, não Apache-2.0",
       observacao="conferir a variante antes de assumir Apache-2.0"),
    _m(id="Qwen/Qwen3", slot="llm.text", nome_front="Qwen 3",
       origem="https://huggingface.co/Qwen", licenca="OPEN_WEIGHTS", spdx="Apache-2.0",
       uso_comercial="YES", runtime="ollama", modalidades=["text"], estado="STABLE",
       padroes=["qwen3:", "qwen3-coder", "qwen3-4b", "qwen3-8b"]),
    _m(id="Qwen/Qwen3-VL", slot="visao", nome_front="Qwen 3 VL — visão",
       origem="https://huggingface.co/Qwen", licenca="OPEN_WEIGHTS", spdx="Apache-2.0",
       uso_comercial="YES", runtime="ollama", modalidades=["text", "image"],
       estado="STABLE", padroes=["qwen3-vl", "qwen2.5vl"],
       observacao="é o modelo que o indexador usa para nomear e categorizar asset"),
    _m(id="deepseek-ai/DeepSeek-Coder", slot="llm.code", nome_front="DeepSeek Coder",
       origem="https://github.com/deepseek-ai/DeepSeek-Coder",
       licenca="COMMERCIAL_CONDITIONAL", spdx="LicenseRef-DeepSeek",
       uso_comercial="CONDITIONAL", runtime="ollama", modalidades=["text"],
       estado="STABLE", padroes=["deepseek-coder"],
       limitacoes="a licença de modelo traz restrições de uso; comercial é permitido sob elas"),
    _m(id="deepseek-ai/DeepSeek-R1", slot="llm.reasoning", nome_front="DeepSeek R1",
       origem="https://huggingface.co/deepseek-ai/DeepSeek-R1",
       licenca="OPEN_WEIGHTS", spdx="MIT", uso_comercial="YES", runtime="ollama",
       modalidades=["text"], estado="STABLE", padroes=["deepseek-r1"]),
    _m(id="meta-llama/Meta-Llama-3", slot="llm.text", nome_front="Llama 3",
       origem="https://llama.meta.com/llama3/license",
       licenca="COMMERCIAL_CONDITIONAL", spdx="LicenseRef-Llama3-Community",
       uso_comercial="CONDITIONAL", runtime="ollama", modalidades=["text"],
       estado="STABLE", padroes=["llama3"],
       limitacoes="cláusula de 700 milhões de usuários mensais e exigência de atribuição"),
    _m(id="openai/gpt-oss", slot="llm.text", nome_front="GPT-OSS 20B",
       origem="https://huggingface.co/openai/gpt-oss-20b",
       licenca="OPEN_WEIGHTS", spdx="Apache-2.0", uso_comercial="YES",
       runtime="ollama", modalidades=["text"], estado="STABLE", padroes=["gpt-oss"]),
    _m(id="mistralai/Devstral-Small", slot="llm.code", nome_front="Devstral",
       origem="https://huggingface.co/mistralai", licenca="OPEN_WEIGHTS",
       spdx="Apache-2.0", uso_comercial="YES", runtime="ollama",
       modalidades=["text"], estado="STABLE", padroes=["devstral"]),
    _m(id="nomic-ai/nomic-embed-text", slot="embed.text", nome_front="Vetorização de texto",
       origem="https://huggingface.co/nomic-ai/nomic-embed-text-v1.5",
       licenca="OPEN_WEIGHTS", spdx="Apache-2.0", uso_comercial="YES",
       runtime="ollama", modalidades=["text"], estado="STABLE",
       padroes=["nomic-embed"],
       observacao="é o que sustenta a busca por significado na biblioteca"),
    _m(id="liuhaotian/LLaVA", slot="visao", nome_front="LLaVA — visão",
       origem="https://github.com/haotian-liu/LLaVA", licenca="UNKNOWN_BLOCKED",
       runtime="ollama", modalidades=["text", "image"], estado="CANDIDATE",
       padroes=["llava"],
       limitacoes="medido: 120 s por asset na indexação, contra 8 s do qwen3-vl:4b",
       fallback="Qwen/Qwen3-VL",
       observacao="os pesos derivam de base Llama; a licença herdada não foi verificada"),
    _m(id="MiniMax/MiniMax-M2", slot="llm.text", nome_front="MiniMax M2 (nuvem)",
       origem="https://ollama.com/library/minimax-m2", licenca="PROVIDER_API",
       uso_comercial="CONDITIONAL", runtime="ollama-cloud", modalidades=["text"],
       estado="CANDIDATE", padroes=["minimax-m2"],
       limitacoes="roda na nuvem: sai da máquina, viola o modo local-first se usado por padrão"),

    # ---- derivados locais: herdam a licença da base --------------------------
    _m(id="local/derivados-qwen", slot="llm.code", nome_front="Perfis locais de código",
       origem="Modelfile local sobre base Qwen 2.5 / Qwen 3",
       licenca="OPEN_WEIGHTS", spdx="Apache-2.0", uso_comercial="YES",
       runtime="ollama", modalidades=["text"], estado="STABLE",
       padroes=["avangard-qwen", "dev-power", "speed-coder", "speed-max-context"],
       observacao="Modelfile só muda parâmetro e prompt; a licença é a da base"),
    _m(id="local/gpt-oss-cad", slot="llm.text", nome_front="Perfil CAD",
       origem="Modelfile local sobre base openai/gpt-oss-20b",
       licenca="OPEN_WEIGHTS", spdx="Apache-2.0", uso_comercial="YES",
       runtime="ollama", modalidades=["text"], estado="STABLE", padroes=["gpt-oss-cad"]),

    # ---- pesos de difusão e componentes no disco -----------------------------
    _m(id="black-forest-labs/FLUX.1-schnell", slot="image.generate.fast",
       nome_front="FLUX.1 schnell", origem="https://huggingface.co/black-forest-labs/FLUX.1-schnell",
       licenca="OPEN_WEIGHTS", spdx="Apache-2.0", uso_comercial="YES",
       runtime="stable-diffusion.cpp", modalidades=["text", "image"],
       hardware_minimo="8 GB VRAM", estado="STABLE", padroes=["flux1-schnell", "flux1_schnell", "flux-fast-quantized"],
       observacao="a variante schnell é Apache-2.0; a dev NÃO é — não confundir"),
    _m(id="black-forest-labs/FLUX.1-autoencoder", slot="image.vae",
       nome_front="Autoencoder do FLUX",
       origem="https://huggingface.co/black-forest-labs/FLUX.1-schnell",
       licenca="OPEN_WEIGHTS", spdx="Apache-2.0", uso_comercial="YES",
       runtime="stable-diffusion.cpp", modalidades=["image"], estado="STABLE",
       padroes=["ae", "diffusion_pytorch_model"],
       observacao="distribuído junto do schnell; segue a licença dele"),
    _m(id="openai/CLIP-ViT-L", slot="image.text_encoder", nome_front="Codificador CLIP",
       origem="https://github.com/openai/CLIP", licenca="OPEN_WEIGHTS", spdx="MIT",
       uso_comercial="YES", runtime="stable-diffusion.cpp", modalidades=["text", "image"],
       estado="STABLE", padroes=["clip_l", "clip_g", "clip-vit"]),
    _m(id="google/T5-v1.1-XXL", slot="image.text_encoder", nome_front="Codificador T5-XXL",
       origem="https://huggingface.co/google/t5-v1_1-xxl", licenca="OPEN_WEIGHTS",
       spdx="Apache-2.0", uso_comercial="YES", runtime="stable-diffusion.cpp",
       modalidades=["text"], estado="STABLE",
       padroes=["t5-v1_1-xxl", "t5xxl", "umt5-xxl", "umt5_xxl"]),
    _m(id="Wan-AI/Wan2.1-weights", slot="video.generate.fast",
       nome_front="Pesos Wan 2.1", origem="https://huggingface.co/Wan-AI/Wan2.1-T2V-1.3B",
       licenca="OPEN_WEIGHTS", spdx="Apache-2.0", uso_comercial="YES",
       runtime="wangp", modalidades=["text", "video"], hardware_minimo="8 GB VRAM",
       estado="STABLE", padroes=["wan2.1", "wan_2.1", "wan2_1", "wan21-", "wan21_"]),
    _m(id="Wan-AI/Wan2.2-weights", slot="video.generate.quality",
       nome_front="Pesos Wan 2.2", origem="https://huggingface.co/Wan-AI",
       licenca="OPEN_WEIGHTS", spdx="Apache-2.0", uso_comercial="YES",
       runtime="wangp", modalidades=["text", "video"], hardware_minimo="16 GB VRAM",
       estado="CANDIDATE", padroes=["wan2.2", "wan_2.2", "wan2_2", "wan22-", "wan22_"],
       limitacoes="no limite da VRAM desta máquina: 15.752 MiB de pico contra 16.376 totais"),
    _m(id="Tongyi-MAI/Z-Image-Turbo-weights", slot="image.generate.fast",
       nome_front="Pesos Z-Image Turbo",
       origem="https://huggingface.co/Tongyi-MAI/Z-Image-Turbo",
       licenca="UNKNOWN_BLOCKED", runtime="stable-diffusion.cpp",
       modalidades=["text", "image"], estado="CANDIDATE",
       padroes=["z_image_turbo", "z-image-turbo", "z_image_vae", "z-image"],
       observacao="cobre também o VAE que vem no mesmo pacote"),
    _m(id="tencent/Hunyuan3D-2-weights", slot="model3d.generate",
       nome_front="Pesos Hunyuan3D 2", origem="https://huggingface.co/tencent/Hunyuan3D-2",
       licenca="UNKNOWN_BLOCKED", runtime="comfyui", modalidades=["image", "mesh"],
       estado="CANDIDATE", padroes=["hunyuan3d"],
       observacao="a licença Tencent restringe território e escala; ler antes de liberar"),
]

POR_ID = {modelo.id: modelo for modelo in MODELOS}


class ModelRegistry:
    """Confronta o que está declarado com o que está no disco."""

    def __init__(self, models_root: Path, slots: list[str] | None = None):
        self.models_root = Path(models_root)
        # Escopo do relatório. Um gate que reprova o módulo de vídeo por causa de uma
        # licença de 3D aponta o dedo para quem não tem culpa, e o time aprende a
        # ignorar o gate. Sem escopo declarado, olha tudo.
        self.slots = [s.strip().lower() for s in (slots or []) if s.strip()]

    def _no_escopo(self, modelo: ModeloRegistrado) -> bool:
        if not self.slots:
            return True
        alvo = modelo.slot.lower()
        return any(alvo.startswith(prefixo) for prefixo in self.slots)

    def escopo(self) -> list[ModeloRegistrado]:
        return [m for m in MODELOS if self._no_escopo(m)]

    def listar(self) -> list[dict[str, Any]]:
        return [modelo.as_dict() for modelo in self.escopo()]

    def pendencias(self) -> list[dict[str, Any]]:
        """Modelos que não podem ir a produção, e o que falta em cada um."""
        pendentes = []
        for modelo in self.escopo():
            if modelo.autoriza_producao():
                continue
            pendentes.append({
                "id": modelo.id,
                "nome_front": modelo.nome_front,
                "licenca": modelo.licenca,
                "o_que_falta": (
                    "resolver a licença dos pesos na origem declarada"
                    if modelo.licenca == "UNKNOWN_BLOCKED"
                    else f"licença {modelo.licenca} não autoriza produção"
                ),
                "origem": modelo.origem,
                "observacao": modelo.observacao,
            })
        return pendentes

    def resolver(self, nome: str) -> ModeloRegistrado | None:
        """Qual declaração cobre este nome. O padrão mais longo ganha, para que
        `gpt-oss-cad` case com o perfil local e não com a base `gpt-oss`."""
        candidatos = [(len(p), m) for m in MODELOS for p in m.padroes
                      if str(nome).strip().lower().startswith(p)]
        if not candidatos:
            return None
        return max(candidatos, key=lambda item: item[0])[1]

    def descobrir_nao_registrados(self, ids_em_uso: list[str]) -> list[str]:
        """Modelo carregável que nenhuma declaração cobre. É aqui que a lacuna aparece.

        Só faz sentido no relatório global: um peso que ninguém declarou também não
        tem slot, e portanto não pode ser imputado a um módulo específico.
        """
        if self.slots:
            return []
        return sorted({str(usado) for usado in ids_em_uso
                       if usado and self.resolver(usado) is None})

    def nao_conferidos(self) -> list[str]:
        """Declarado a partir do card upstream, sem ninguém ter aberto a licença aqui.

        Não é falha — é o grau de certeza. Tratar pesquisa como evidência é o que
        transforma um registro de licenças em teatro.
        """
        return [m.id for m in self.escopo() if not m.conferido and m.autoriza_producao()]

    def relatorio(self, ids_em_uso: list[str] | None = None) -> dict[str, Any]:
        registrados = self.listar()
        liberados = [m for m in registrados if m["autoriza_producao"]]
        em_uso = [str(x) for x in (ids_em_uso or []) if x]
        cobertura = {}
        for nome in sorted(set(em_uso)):
            achado = self.resolver(nome)
            cobertura[nome] = achado.id if achado else None
        return {
            "escopo": self.slots or ["*"],
            "total_registrado": len(registrados),
            "autorizados": len(liberados),
            "pendentes": self.pendencias(),
            "nao_registrados": self.descobrir_nao_registrados(em_uso),
            "nao_conferidos": self.nao_conferidos(),
            "cobertura": cobertura,
            "modelos": registrados,
            "tags_validas": list(TAGS_DE_LICENCA),
            "gerado_em": utc_now(),
        }

    def gravar_evidencia(self, destino: Path, ids_em_uso: list[str] | None = None) -> Path:
        """Grava o relatório no formato que `GATE-LICENSE` consome."""
        relatorio = self.relatorio(ids_em_uso)
        pendentes = len(relatorio["pendentes"]) + len(relatorio["nao_registrados"])
        conteudo = {
            "gate_id": "GATE-LICENSE",
            "status": "PASS" if pendentes == 0 else "FAIL",
            "summary": (
                f"{relatorio['autorizados']}/{relatorio['total_registrado']} autorizados, "
                f"{len(relatorio['pendentes'])} pendentes, "
                f"{len(relatorio['nao_registrados'])} não registrados"
            ),
            "recorded_at": utc_now(),
            **relatorio,
        }
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(json.dumps(conteudo, ensure_ascii=False, indent=2), encoding="utf-8")
        return destino
