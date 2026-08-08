"""Executor da Fase E: pega um asset real, roda o cálculo, grava o resultado.

Regra que sustenta o resto: se o cálculo não existir para um `feature_id`, este
motor recusa com código. Ele nunca devolve um dicionário plausível para dar a
impressão de que a operação rodou — foi exatamente essa impressão que os 1697
stubs em Rust produziram, e é o que este módulo existe para não repetir.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from ..util import new_id, sha256_file, utc_now
from .registry import POR_FEATURE, OperacaoPerzon


class PerzonOperationError(RuntimeError):
    """Falha nomeada. `codigo` é o que a UI mostra e o que o teste afirma."""

    def __init__(self, codigo: str, mensagem: str, dica: str = ""):
        super().__init__(mensagem)
        self.codigo = codigo
        self.mensagem = mensagem
        self.dica = dica

    def as_dict(self) -> dict[str, str]:
        return {"code": self.codigo, "message": self.mensagem, "hint": self.dica}


class PerzonEngine:
    """Roda uma operação do PERZON sobre um arquivo do disco."""

    def __init__(self, saida_dir: Path, models_root: Path | None = None):
        self.saida_dir = Path(saida_dir)
        # Por padrão, os modelos ficam ao lado da saída, em data/models. Passar o
        # caminho explicitamente é o que permite o teste apontar para outro lugar.
        self.models_root = Path(models_root) if models_root else Path(saida_dir).parent / "models"

    # ---- execução -------------------------------------------------------

    def executar(self, feature_id: str, caminho_entrada: str | None = None,
                 parametros: dict[str, Any] | None = None) -> dict[str, Any]:
        operacao = POR_FEATURE.get(feature_id)
        if operacao is None:
            raise PerzonOperationError(
                "FEATURE_NAO_IMPLEMENTADA",
                f"{feature_id} não tem cálculo implementado neste motor.",
                "O contrato do PERZON existe, o algoritmo não. Veja "
                "/api/perzon/operacoes para o que roda de fato.",
            )

        parametros = dict(parametros or {})
        self._conferir_parametros(operacao, parametros)

        inicio = time.perf_counter()
        if operacao.entrada == "mesh":
            resultado = self._executar_mesh(operacao, caminho_entrada, parametros)
        elif operacao.entrada == "imagem":
            resultado = self._executar_imagem(operacao, caminho_entrada, parametros)
        elif operacao.entrada == "animacao":
            resultado = self._executar_animacao(operacao, caminho_entrada, parametros)
        elif operacao.entrada == "arquivo":
            resultado = self._executar_arquivo(operacao, caminho_entrada, parametros)
        elif operacao.entrada == "rosto":
            resultado = self._executar_rosto(operacao, caminho_entrada, parametros)
        elif operacao.entrada == "cabelo":
            resultado = self._executar_cabelo(operacao, caminho_entrada, parametros)
        else:
            resultado = {"metrica": operacao.funcao(**parametros), "artefatos": []}
        duracao = time.perf_counter() - inicio

        return {
            "feature_id": feature_id,
            "modulo": operacao.modulo,
            "nome": operacao.nome,
            "status": "executado",
            "duracao_s": round(duracao, 4),
            "parametros": parametros,
            **resultado,
            "procedencia": {
                "motor": "cinenode.perzon",
                "local": True,
                "entrada": caminho_entrada,
                "executado_em": utc_now(),
            },
        }

    def _conferir_parametros(self, operacao: OperacaoPerzon,
                             parametros: dict[str, Any]) -> None:
        """Faixa declarada é contrato. Deixar passar valor fora dela empurra a
        falha para dentro do cálculo, onde a mensagem já não diz o que fazer.

        O padrão declarado também é aplicado aqui. Sem isso, um parâmetro
        obrigatório na função e opcional no contrato explode como `TypeError` —
        que é erro de programação vazando como se fosse erro do usuário.
        """
        for chave, regra in operacao.parametros.items():
            if chave not in parametros and "padrao" in regra:
                parametros[chave] = regra["padrao"]

        for chave, valor in list(parametros.items()):
            regra = operacao.parametros.get(chave)
            if regra is None:
                raise PerzonOperationError(
                    "PARAMETRO_DESCONHECIDO",
                    f"{operacao.feature_id} não aceita o parâmetro '{chave}'.",
                    f"Aceita: {', '.join(operacao.parametros) or 'nenhum'}",
                )
            if regra["tipo"] == "inteiro":
                valor = int(valor)
            elif regra["tipo"] == "decimal":
                valor = float(valor)
            elif regra["tipo"] == "lista":
                # Vetor de direção, por exemplo. Faixa não se aplica a lista, e
                # converter para float aqui explodiria numa sequência.
                if not isinstance(valor, (list, tuple)):
                    raise PerzonOperationError(
                        "PARAMETRO_FORA_DA_FAIXA",
                        f"{chave} precisa ser uma lista, veio {type(valor).__name__}.", "")
                parametros[chave] = list(valor)
                continue
            minimo, maximo = regra.get("minimo"), regra.get("maximo")
            if minimo is not None and valor < minimo:
                raise PerzonOperationError(
                    "PARAMETRO_FORA_DA_FAIXA",
                    f"{chave}={valor} abaixo do mínimo {minimo}.", "")
            if maximo is not None and valor > maximo:
                raise PerzonOperationError(
                    "PARAMETRO_FORA_DA_FAIXA",
                    f"{chave}={valor} acima do máximo {maximo}.", "")
            parametros[chave] = valor

    # ---- malha ----------------------------------------------------------

    def _executar_mesh(self, operacao: OperacaoPerzon, caminho: str | None,
                       parametros: dict[str, Any]) -> dict[str, Any]:
        from . import mesh_ops, rig_ops

        malha = self._carregar_malha(caminho)

        # O rig precisa do esqueleto antes dos pesos, e a validação precisa dos dois.
        # Encadear aqui evita que a UI tenha de conhecer a ordem.
        if operacao.feature_id == "PZ-11-peso-automatico":
            esqueleto = rig_ops.gerar_esqueleto(malha)
            return {"metrica": rig_ops.calcular_pesos(malha, esqueleto, **parametros),
                    "artefatos": []}
        if operacao.feature_id == "PZ-11-validar-hierarquia":
            esqueleto = rig_ops.gerar_esqueleto(malha)
            pesos = rig_ops.calcular_pesos(malha, esqueleto)
            defeitos = rig_ops.validar_rig(esqueleto, pesos)
            return {"metrica": {"defeitos": defeitos, "aprovado": not defeitos},
                    "artefatos": []}
        if operacao.feature_id == "PZ-06-grupos-semanticos":
            componentes = malha.split(only_watertight=False)
            return {"metrica": {"grupos": [
                {"indice": i, "vertices": int(len(c.vertices)), "faces": int(len(c.faces)),
                 "volume": float(c.volume) if c.is_watertight else None,
                 "dimensoes": [round(float(x), 6) for x in c.extents]}
                for i, c in enumerate(componentes)], "total": len(componentes)},
                "artefatos": []}
        if operacao.feature_id == "PZ-06-topologia-estavel":
            diagnostico = mesh_ops.diagnosticar(malha)
            return {"metrica": {**diagnostico, "defeitos": mesh_ops.problemas(diagnostico)},
                    "artefatos": []}

        # Exportação escreve o arquivo ela mesma, com nome e extensão próprios —
        # não passa pelo `_gravar_malha`, que grava sempre GLB de geometria pura.
        if operacao.modulo == "formats":
            return self._exportar(operacao, malha)

        try:
            saida = operacao.funcao(malha, **parametros)
        except (mesh_ops.MalhaInvalida, rig_ops.RigInvalido) as erro:
            raise PerzonOperationError("MALHA_NAO_SUPORTA_OPERACAO", str(erro),
                                       "Rode PZ-06-topologia-estavel para ver os defeitos.") from erro

        if not operacao.produz_asset:
            return {"metrica": saida, "artefatos": []}

        nova_malha, metrica = saida if isinstance(saida, tuple) else (saida, {})
        if isinstance(metrica, list):   # reparar() devolve lista de ações
            metrica = {"acoes": metrica}
        destino = self._gravar_malha(nova_malha, operacao)
        return {"metrica": metrica, "artefatos": [destino]}

    def _carregar_malha(self, caminho: str | None):
        from . import mesh_ops

        if not caminho:
            raise PerzonOperationError("ENTRADA_AUSENTE",
                                       "Esta operação precisa de uma malha.",
                                       "Envie um arquivo .glb, .obj, .ply ou .stl.")
        arquivo = Path(caminho)
        if not arquivo.is_file():
            raise PerzonOperationError("ARQUIVO_INEXISTENTE", f"{caminho} não existe.", "")
        try:
            return mesh_ops.carregar(str(arquivo))
        except mesh_ops.MalhaInvalida as erro:
            raise PerzonOperationError("MALHA_INVALIDA", str(erro),
                                       "Confira se o arquivo tem geometria triangular.") from erro

    def _gravar_malha(self, malha, operacao: OperacaoPerzon) -> dict[str, Any]:
        pasta = self.saida_dir / "perzon"
        pasta.mkdir(parents=True, exist_ok=True)
        destino = pasta / f"{operacao.modulo}_{new_id('pz')}.glb"
        destino.write_bytes(malha.export(file_type="glb"))
        return {
            "caminho": str(destino), "tipo": "model3d", "formato": "glb",
            "bytes": destino.stat().st_size, "sha256": sha256_file(destino),
            "vertices": int(len(malha.vertices)), "faces": int(len(malha.faces)),
        }

    # ---- rosto ----------------------------------------------------------

    # Cada operação de rosto precisa de um recorte diferente do mesmo resultado:
    # umas querem os 478 pontos, outras as 52 blendshapes, outras a matriz de
    # transformação. A tabela evita um `if` por operação dentro do executor.
    _ARGUMENTOS_DE_ROSTO: dict[str, tuple[str, ...]] = {
        "PZ-05-shapes-de-expressao": ("blendshapes",),
        "PZ-05-controles-facs": ("blendshapes",),
        "PZ-05-visemas": ("blendshapes",),
        "PZ-05-espelhar-expressao": ("blendshapes",),
        "PZ-05-corretivos": ("blendshapes",),
        "PZ-05-fechamento-dos-olhos": ("pontos",),
        "PZ-05-contato-dos-labios": ("pontos",),
        "PZ-05-assimetria": ("pontos",),
        "PZ-04-deteccao-do-rosto": ("imagem", "pontos"),
        "PZ-04-mascaras-de-pele-cabelo-e-fundo": ("imagem", "pontos"),
        "PZ-04-alinhar": ("imagem", "pontos"),
        "PZ-04-correcao-de-perspectiva": ("matriz",),
        "PZ-04-analisar-fotos": ("imagem", "pontos", "matriz"),
    }

    def _detectar_rosto(self, caminho: Path) -> dict[str, Any]:
        """Roda o FaceLandmarker uma vez e devolve tudo o que ele produz.

        Uma inferência por foto, não uma por operação: pedir blendshapes depois de
        já ter pedido os pontos custaria o passe inteiro de novo sobre a mesma
        imagem, e são ~1,9 s no caso mais lento medido neste projeto.
        """
        import cv2
        import mediapipe as mp
        import numpy as np
        from mediapipe.tasks import python as mpp
        from mediapipe.tasks.python import vision

        modelo = self.models_root / "mediapipe" / "face_landmarker.task"
        if not modelo.is_file():
            raise PerzonOperationError(
                "MODELO_AUSENTE", f"face_landmarker.task não está em {modelo.parent}.",
                "Rode scripts/install_vision_models.py ou baixe de "
                "https://storage.googleapis.com/mediapipe-models/")

        imagem = cv2.imread(str(caminho), cv2.IMREAD_COLOR)
        if imagem is None:
            raise PerzonOperationError("IMAGEM_INVALIDA",
                                       f"não consegui ler {caminho} como imagem.", "")

        opcoes = vision.FaceLandmarkerOptions(
            base_options=mpp.BaseOptions(model_asset_path=str(modelo)),
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
            num_faces=1,
        )
        with vision.FaceLandmarker.create_from_options(opcoes) as detector:
            resultado = detector.detect(mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=cv2.cvtColor(imagem, cv2.COLOR_BGR2RGB)))

        if not resultado.face_landmarks:
            raise PerzonOperationError(
                "ROSTO_NAO_ENCONTRADO", f"nenhum rosto detectado em {Path(caminho).name}.",
                "Use uma foto com o rosto visível e iluminado.")

        altura, largura = imagem.shape[:2]
        # Os pontos vêm normalizados: x pela largura e y pela altura. Numa imagem
        # não quadrada, medir sem desnormalizar infla toda distância vertical —
        # foi assim que a razão altura/largura do rosto saiu 2,9 em vez de 1,4.
        pontos = np.array([[p.x * largura, p.y * altura, p.z * largura]
                           for p in resultado.face_landmarks[0]], dtype=np.float64)

        matrizes = getattr(resultado, "facial_transformation_matrixes", None)
        return {
            "imagem": imagem,
            "pontos": pontos,
            "blendshapes": resultado.face_blendshapes[0] if resultado.face_blendshapes else [],
            "matriz": matrizes[0] if matrizes else None,
        }

    def _executar_rosto(self, operacao: OperacaoPerzon, caminho: str | None,
                        parametros: dict[str, Any]) -> dict[str, Any]:
        import cv2

        from . import face_ops, headshot_ops

        if not caminho:
            raise PerzonOperationError("ENTRADA_AUSENTE",
                                       "Esta operação precisa de uma foto de rosto.", "")
        arquivo = Path(caminho)
        if not arquivo.is_file():
            raise PerzonOperationError("ARQUIVO_INEXISTENTE", f"{caminho} não existe.", "")

        leitura = self._detectar_rosto(arquivo)
        nomes = self._ARGUMENTOS_DE_ROSTO.get(operacao.feature_id, ("pontos",))
        argumentos = [leitura[nome] for nome in nomes]

        if "matriz" in nomes and leitura["matriz"] is None:
            raise PerzonOperationError(
                "MATRIZ_AUSENTE",
                "O detector não devolveu a matriz de transformação facial.",
                "Sem ela não há como medir guinada; a operação recusa em vez de "
                "devolver zero grau como se o rosto estivesse frontal.")

        try:
            saida = operacao.funcao(*argumentos, **parametros)
        except (face_ops.RostoInvalido, headshot_ops.FotoInvalida) as erro:
            raise PerzonOperationError("ROSTO_NAO_SUPORTA_OPERACAO", str(erro), "") from erro

        if not operacao.produz_asset:
            metrica = {"defeitos": saida, "aprovado": not saida} if isinstance(saida, list) else saida
            return {"metrica": metrica, "artefatos": []}

        recorte, metrica = saida
        pasta = self.saida_dir / "perzon"
        pasta.mkdir(parents=True, exist_ok=True)
        destino = pasta / f"rosto_{new_id('pz')}.png"
        if not cv2.imwrite(str(destino), recorte):
            raise PerzonOperationError("FALHA_AO_GRAVAR", f"cv2 não gravou {destino}", "")
        return {"metrica": metrica, "artefatos": [{
            "caminho": str(destino), "tipo": "image", "formato": "png",
            "bytes": destino.stat().st_size, "sha256": sha256_file(destino),
            "resolucao": [int(recorte.shape[1]), int(recorte.shape[0])],
        }]}

    # ---- cabelo ---------------------------------------------------------

    def _executar_cabelo(self, operacao: OperacaoPerzon, caminho: str | None,
                         parametros: dict[str, Any]) -> dict[str, Any]:
        """Guias de cabelo em JSON: `{"guias": [[[x,y,z], ...], ...]}`.

        O mesmo formato simples do clipe de animação, pelo mesmo motivo: pôr um
        analisador de Alembic entre o usuário e o cálculo adiaria justamente o
        cálculo, que é o que faltava.
        """
        import json

        import numpy as np

        from . import hair_ops

        if not caminho:
            raise PerzonOperationError(
                "ENTRADA_AUSENTE", "Esta operação precisa de guias de cabelo.",
                'Envie JSON com {"guias": [[[x,y,z], ...], ...]}.')
        arquivo = Path(caminho)
        if not arquivo.is_file():
            raise PerzonOperationError("ARQUIVO_INEXISTENTE", f"{caminho} não existe.", "")

        try:
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
            guias = np.asarray(dados["guias"], dtype=np.float64)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as erro:
            raise PerzonOperationError(
                "GUIAS_INVALIDAS", f"{arquivo.name} não traz guias legíveis: {erro}",
                'Esperado {"guias": [[[x,y,z], ...], ...]}.') from erro

        chamada = dict(parametros)
        if operacao.feature_id == "PZ-09-prender-a-superficie" and dados.get("couro"):
            import trimesh

            chamada["couro"] = trimesh.load(str(dados["couro"]), force="mesh", process=False)

        try:
            saida = operacao.funcao(guias, **chamada)
        except hair_ops.CabeloInvalido as erro:
            raise PerzonOperationError("CABELO_INVALIDO", str(erro), "") from erro

        if not isinstance(saida, tuple):
            metrica = ({"defeitos": saida, "aprovado": not saida}
                       if isinstance(saida, list) else saida)
            return {"metrica": metrica, "artefatos": []}

        resultado, metrica = saida
        pasta = self.saida_dir / "perzon"
        pasta.mkdir(parents=True, exist_ok=True)

        # `converter_em_cards` devolve malha; as demais devolvem guias novas.
        if hasattr(resultado, "faces"):
            destino = pasta / f"cabelo_{new_id('pz')}.glb"
            destino.write_bytes(resultado.export(file_type="glb"))
            tipo, formato = "model3d", "glb"
        else:
            destino = pasta / f"cabelo_{new_id('pz')}.json"
            destino.write_text(json.dumps({
                "guias": np.round(np.asarray(resultado), 6).tolist(),
                "couro": dados.get("couro", ""),
            }, ensure_ascii=False), encoding="utf-8")
            tipo, formato = "data", "json"

        return {"metrica": metrica, "artefatos": [{
            "caminho": str(destino), "tipo": tipo, "formato": formato,
            "bytes": destino.stat().st_size, "sha256": sha256_file(destino),
        }]}

    # ---- exportação -----------------------------------------------------

    def _exportar(self, operacao: OperacaoPerzon, malha) -> dict[str, Any]:
        """Exporta a malha, com rig quando o formato carrega rig.

        O esqueleto e os pesos são calculados aqui, na hora. Exigir que o chamador
        passe os dois transformaria a exportação num terceiro passo obrigatório, e
        o erro mais comum passaria a ser exportar sem rig por esquecimento.
        """
        from . import export_ops, rig_ops

        pasta = self.saida_dir / "perzon"
        pasta.mkdir(parents=True, exist_ok=True)

        if operacao.feature_id == "PZ-26-obj":
            destino = pasta / f"personagem_{new_id('pz')}.obj"
            metrica = export_ops.exportar_obj(malha, destino)
            tipo, formato = "model3d", "obj"
        else:
            destino = pasta / f"personagem_{new_id('pz')}.glb"
            esqueleto = rig_ops.gerar_esqueleto(malha)
            pesos = rig_ops.calcular_pesos(malha, esqueleto)
            metrica = export_ops.exportar_gltf(malha, destino, esqueleto, pesos)
            # Relê e confere o que acabou de gravar. Gravar e afirmar sucesso sem
            # abrir o arquivo é como os 1697 stubs afirmavam ter rodado.
            metrica["validacao"] = export_ops.validar_gltf(destino)
            tipo, formato = "model3d", "glb"

        return {"metrica": metrica, "artefatos": [{
            "caminho": str(destino), "tipo": tipo, "formato": formato,
            "bytes": destino.stat().st_size, "sha256": sha256_file(destino),
            "vertices": int(len(malha.vertices)), "faces": int(len(malha.faces)),
        }]}

    def _executar_arquivo(self, operacao: OperacaoPerzon, caminho: str | None,
                          parametros: dict[str, Any]) -> dict[str, Any]:
        """Operação que inspeciona um arquivo já gravado, sem interpretá-lo antes."""
        if not caminho:
            raise PerzonOperationError("ENTRADA_AUSENTE",
                                       "Esta operação precisa de um arquivo.", "")
        arquivo = Path(caminho)
        if not arquivo.is_file():
            raise PerzonOperationError("ARQUIVO_INEXISTENTE", f"{caminho} não existe.", "")
        return {"metrica": operacao.funcao(arquivo, **parametros), "artefatos": []}

    # ---- animação -------------------------------------------------------

    def _executar_animacao(self, operacao: OperacaoPerzon, caminho: str | None,
                           parametros: dict[str, Any]) -> dict[str, Any]:
        """Lê o clipe do JSON, roda o cálculo, grava o clipe novo quando há um.

        O formato é deliberadamente simples: `{"fps": 30, "juntas": [...],
        "quadros": [[[x,y,z], ...], ...]}`. Amarrar isto a FBX ou BVH agora
        colocaria um analisador de formato binário entre o usuário e o cálculo,
        e o cálculo é o que estava faltando.
        """
        import json

        import numpy as np

        from . import motion_ops

        if not caminho:
            raise PerzonOperationError(
                "ENTRADA_AUSENTE", "Esta operação precisa de um clipe de animação.",
                'Envie JSON com {"fps": ..., "quadros": [[[x,y,z], ...], ...]}.')
        arquivo = Path(caminho)
        if not arquivo.is_file():
            raise PerzonOperationError("ARQUIVO_INEXISTENTE", f"{caminho} não existe.", "")

        try:
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
            quadros = np.asarray(dados["quadros"], dtype=np.float64)
            fps = float(dados["fps"])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as erro:
            raise PerzonOperationError(
                "CLIPE_INVALIDO", f"{arquivo.name} não é um clipe legível: {erro}",
                'Esperado {"fps": número, "quadros": [[[x,y,z], ...], ...]}.') from erro

        # Operação de pé precisa saber quais juntas são pé; sem isso ela não tem
        # como distinguir apoio de qualquer outra parte do corpo.
        chamada = dict(parametros)
        if "juntas_pe" in operacao.funcao.__code__.co_varnames:
            juntas_pe = dados.get("juntas_pe")
            if not juntas_pe:
                raise PerzonOperationError(
                    "JUNTAS_DE_PE_AUSENTES",
                    "O clipe não declara quais índices são os pés.",
                    'Inclua "juntas_pe": [i, j] no JSON do clipe.')
            chamada["juntas_pe"] = [int(x) for x in juntas_pe]

        # BVH grava hierarquia, então precisa do esqueleto — e ele não é dedutível
        # de uma nuvem de posições: as mesmas coordenadas servem a mais de uma
        # árvore de ossos, e escolher uma seria inventar o rig do usuário.
        if operacao.feature_id == "PZ-26-bvh":
            from . import export_ops

            esqueleto = dados.get("esqueleto")
            if not esqueleto or "juntas" not in esqueleto:
                raise PerzonOperationError(
                    "ESQUELETO_AUSENTE",
                    "BVH grava hierarquia; o clipe não traz esqueleto.",
                    'Rode PZ-11-criar-rig e inclua o resultado em "esqueleto".')
            pasta = self.saida_dir / "perzon"
            pasta.mkdir(parents=True, exist_ok=True)
            destino = pasta / f"motion_{new_id('pz')}.bvh"
            try:
                metrica = export_ops.exportar_bvh(esqueleto, quadros, fps, destino)
            except export_ops.ExportacaoInvalida as erro:
                raise PerzonOperationError("EXPORTACAO_INVALIDA", str(erro), "") from erro
            return {"metrica": metrica, "artefatos": [{
                "caminho": str(destino), "tipo": "data", "formato": "bvh",
                "bytes": destino.stat().st_size, "sha256": sha256_file(destino),
                "quadros": int(quadros.shape[0]), "fps": float(fps),
            }]}

        try:
            saida = operacao.funcao(quadros, fps, **chamada)
        except motion_ops.AnimacaoInvalida as erro:
            raise PerzonOperationError("ANIMACAO_INVALIDA", str(erro), "") from erro

        if not isinstance(saida, tuple):
            return {"metrica": saida, "artefatos": []}

        novos_quadros, metrica = saida
        fps_saida = metrica.get("fps_depois", fps)
        pasta = self.saida_dir / "perzon"
        pasta.mkdir(parents=True, exist_ok=True)
        destino = pasta / f"motion_{new_id('pz')}.json"
        destino.write_text(json.dumps({
            "fps": fps_saida,
            "juntas": dados.get("juntas", []),
            "juntas_pe": dados.get("juntas_pe", []),
            "quadros": np.round(novos_quadros, 6).tolist(),
        }, ensure_ascii=False), encoding="utf-8")

        return {"metrica": metrica, "artefatos": [{
            "caminho": str(destino), "tipo": "data", "formato": "json",
            "bytes": destino.stat().st_size, "sha256": sha256_file(destino),
            "quadros": int(novos_quadros.shape[0]), "fps": float(fps_saida),
        }]}

    # ---- imagem ---------------------------------------------------------

    def _executar_imagem(self, operacao: OperacaoPerzon, caminho: str | None,
                         parametros: dict[str, Any]) -> dict[str, Any]:
        import cv2

        from . import material_ops

        if not caminho:
            raise PerzonOperationError("ENTRADA_AUSENTE",
                                       "Esta operação precisa de uma imagem.", "")
        arquivo = Path(caminho)
        if not arquivo.is_file():
            raise PerzonOperationError("ARQUIVO_INEXISTENTE", f"{caminho} não existe.", "")
        try:
            imagem = material_ops.carregar(str(arquivo))
        except material_ops.ImagemInvalida as erro:
            raise PerzonOperationError("IMAGEM_INVALIDA", str(erro), "") from erro

        saida = operacao.funcao(imagem, **parametros)

        if not operacao.produz_asset:
            metrica = {"defeitos": saida, "aprovado": not saida} if isinstance(saida, list) else saida
            return {"metrica": metrica, "artefatos": []}

        mapa, metrica = saida
        pasta = self.saida_dir / "perzon"
        pasta.mkdir(parents=True, exist_ok=True)
        destino = pasta / f"{operacao.feature_id.replace('-', '_')}_{new_id('pz')}.png"
        if not cv2.imwrite(str(destino), mapa):
            raise PerzonOperationError("FALHA_AO_GRAVAR", f"cv2 não gravou {destino}", "")
        return {"metrica": metrica, "artefatos": [{
            "caminho": str(destino), "tipo": "image", "formato": "png",
            "bytes": destino.stat().st_size, "sha256": sha256_file(destino),
            "resolucao": [int(mapa.shape[1]), int(mapa.shape[0])],
        }]}
