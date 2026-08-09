from __future__ import annotations

from pathlib import Path
import json
import textwrap

ROOT = Path(__file__).resolve().parents[1]


def write(path: str, value: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(textwrap.dedent(value).lstrip("\n"), encoding="utf-8", newline="\n")


write(
    "src/cinenode/models.py",
    r'''
    from __future__ import annotations

    from dataclasses import asdict, dataclass
    from pathlib import Path
    from typing import Any
    from urllib.parse import urlsplit
    from urllib.request import Request, urlopen
    import hashlib
    import json
    import os
    import tempfile


    @dataclass(frozen=True, slots=True)
    class ModelSpec:
        id: str
        name: str
        filename: str
        url: str
        sha256: str
        max_bytes: int
        license: str
        engine: str
        description: str = ""

        @classmethod
        def from_dict(cls, value: dict[str, Any]) -> "ModelSpec":
            spec = cls(
                id=str(value["id"]),
                name=str(value["name"]),
                filename=Path(str(value["filename"])).name,
                url=str(value["url"]),
                sha256=str(value["sha256"]).lower(),
                max_bytes=int(value["max_bytes"]),
                license=str(value.get("license", "UNKNOWN")),
                engine=str(value["engine"]),
                description=str(value.get("description", "")),
            )
            spec.validate()
            return spec

        def validate(self) -> None:
            if not self.id or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789._-" for char in self.id):
                raise ValueError("model id must be lowercase and filesystem safe")
            parsed = urlsplit(self.url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError("model URL must be credential-free HTTPS")
            if len(self.sha256) != 64 or any(char not in "0123456789abcdef" for char in self.sha256):
                raise ValueError("model manifest requires an expected SHA-256")
            if self.max_bytes < 1:
                raise ValueError("model max_bytes must be positive")


    class ModelManager:
        """Manifest-only model installer.

        Arbitrary URLs are intentionally not accepted by the API. A model must first be reviewed and
        entered in the repository/deployment manifest with an expected SHA-256 and size ceiling.
        """

        def __init__(self, root: Path, manifest_path: Path):
            self.root = Path(root).resolve()
            self.manifest_path = Path(manifest_path)
            self._specs = self._load()

        def _load(self) -> dict[str, ModelSpec]:
            value = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            specs = [ModelSpec.from_dict(item) for item in value.get("models", [])]
            result = {spec.id: spec for spec in specs}
            if len(result) != len(specs):
                raise ValueError("duplicate model id in manifest")
            return result

        def list(self) -> list[dict[str, Any]]:
            result = []
            for spec in self._specs.values():
                path = self.root / spec.engine / spec.filename
                item = asdict(spec)
                item.update({"installed": self._matches(path, spec.sha256), "path": str(path)})
                item.pop("url", None)
                result.append(item)
            return sorted(result, key=lambda item: item["id"])

        def get(self, model_id: str) -> ModelSpec:
            try:
                return self._specs[model_id]
            except KeyError as exc:
                raise KeyError(f"unknown model: {model_id}") from exc

        def install(self, model_id: str) -> dict[str, Any]:
            spec = self.get(model_id)
            destination = (self.root / spec.engine / spec.filename).resolve()
            if self.root not in destination.parents:
                raise ValueError("unsafe model path")
            destination.parent.mkdir(parents=True, exist_ok=True)
            if self._matches(destination, spec.sha256):
                return {"id": spec.id, "installed": True, "cached": True, "path": str(destination)}

            request = Request(spec.url, headers={"User-Agent": "CineNode/1.0 model-installer"})
            fd, temporary_name = tempfile.mkstemp(prefix=f".{spec.filename}.", suffix=".part", dir=destination.parent)
            temporary = Path(temporary_name)
            digest = hashlib.sha256()
            size = 0
            try:
                with os.fdopen(fd, "wb") as output, urlopen(request, timeout=60) as response:
                    announced = response.headers.get("Content-Length")
                    if announced and int(announced) > spec.max_bytes:
                        raise ValueError("model exceeds manifest size ceiling")
                    while chunk := response.read(1024 * 1024):
                        size += len(chunk)
                        if size > spec.max_bytes:
                            raise ValueError("model exceeds manifest size ceiling")
                        digest.update(chunk)
                        output.write(chunk)
                    output.flush()
                    os.fsync(output.fileno())
                if digest.hexdigest() != spec.sha256:
                    raise ValueError("model SHA-256 mismatch")
                os.replace(temporary, destination)
            except Exception:
                temporary.unlink(missing_ok=True)
                raise
            return {
                "id": spec.id,
                "installed": True,
                "cached": False,
                "path": str(destination),
                "bytes": size,
                "sha256": digest.hexdigest(),
            }

        @staticmethod
        def _matches(path: Path, expected: str) -> bool:
            if not path.is_file():
                return False
            digest = hashlib.sha256()
            with path.open("rb") as source:
                while chunk := source.read(1024 * 1024):
                    digest.update(chunk)
            return digest.hexdigest() == expected
    ''',
)

write(
    "src/cinenode/manifests/models.json",
    json.dumps(
        {
            "schema_version": 1,
            "models": [],
            "policy": "Add only reviewed models with license, immutable HTTPS URL, size ceiling and expected SHA-256.",
        },
        indent=2,
    )
    + "\n",
)

write(
    "src/cinenode/engines/llama_cpp.py",
    r'''
    from __future__ import annotations

    from pathlib import Path
    from typing import Any
    import asyncio
    import os

    from .base import EngineAdapter, EngineInfo


    class LlamaCppEngine(EngineAdapter):
        info = EngineInfo("llama-cpp", "llama.cpp in-process", ("chat", "local-model"))

        def __init__(self, model_path: str | Path | None = None):
            configured = model_path or os.getenv("CINENODE_LLAMA_MODEL", "")
            self.model_path = Path(configured).expanduser().resolve() if configured else None
            self._model: Any | None = None
            self._lock = asyncio.Lock()

        async def probe(self) -> dict[str, Any]:
            try:
                import llama_cpp  # noqa: F401
            except ImportError:
                return {"ok": False, "dependency": "llama-cpp-python", "model": str(self.model_path or "")}
            return {
                "ok": bool(self.model_path and self.model_path.is_file()),
                "dependency": "llama-cpp-python",
                "model": str(self.model_path or ""),
            }

        async def chat(self, prompt: str, params: dict[str, Any]) -> str:
            if not self.model_path or not self.model_path.is_file():
                raise ValueError("set CINENODE_LLAMA_MODEL to an installed GGUF file")
            async with self._lock:
                model = await asyncio.to_thread(self._load, params)
                result = await asyncio.to_thread(
                    model.create_chat_completion,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=float(params.get("temperature", 0.7)),
                    max_tokens=int(params.get("max_tokens", 1024)),
                )
            return str(result["choices"][0]["message"]["content"])

        def _load(self, params: dict[str, Any]):
            if self._model is None:
                try:
                    from llama_cpp import Llama
                except ImportError as exc:
                    raise RuntimeError("install CineNode with the llama-cpp extra") from exc
                self._model = Llama(
                    model_path=str(self.model_path),
                    n_ctx=int(params.get("n_ctx", 4096)),
                    n_gpu_layers=int(params.get("n_gpu_layers", -1)),
                    verbose=False,
                )
            return self._model
    ''',
)

# Register the in-process adapter without making llama-cpp-python a core dependency.
registry = ROOT / "src/cinenode/engines/registry.py"
source = registry.read_text(encoding="utf-8")
if "from .llama_cpp import LlamaCppEngine" not in source:
    source = source.replace(
        "from .http_adapters import ComfyUIEngine, MockEngine, OllamaEngine, OpenAICompatibleEngine\n",
        "from .http_adapters import ComfyUIEngine, MockEngine, OllamaEngine, OpenAICompatibleEngine\nfrom .llama_cpp import LlamaCppEngine\n",
    )
if "registry.register(LlamaCppEngine())" not in source:
    source = source.replace(
        "    registry.register(ComfyUIEngine(allow_private=allow_private))\n",
        "    registry.register(ComfyUIEngine(allow_private=allow_private))\n    registry.register(LlamaCppEngine())\n",
    )
registry.write_text(source, encoding="utf-8")

write(
    "src/cinenode/bootstrap.py",
    r'''
    from __future__ import annotations

    from dataclasses import asdict, dataclass
    from pathlib import Path
    from typing import Any
    import os
    import platform
    import shutil
    import subprocess


    @dataclass(frozen=True, slots=True)
    class InstallResult:
        capability: str
        installed: bool
        attempted: bool
        command: tuple[str, ...] = ()
        detail: str = ""


    def recommended_commands() -> dict[str, tuple[str, ...]]:
        system = platform.system().lower()
        if system == "windows" and shutil.which("winget"):
            return {
                "git": ("winget", "install", "--id", "Git.Git", "--exact", "--silent", "--accept-package-agreements", "--accept-source-agreements"),
                "ffmpeg": ("winget", "install", "--id", "Gyan.FFmpeg", "--exact", "--silent", "--accept-package-agreements", "--accept-source-agreements"),
                "ollama": ("winget", "install", "--id", "Ollama.Ollama", "--exact", "--silent", "--accept-package-agreements", "--accept-source-agreements"),
            }
        if system == "darwin" and shutil.which("brew"):
            return {
                "git": ("brew", "install", "git"),
                "ffmpeg": ("brew", "install", "ffmpeg"),
                "ollama": ("brew", "install", "ollama"),
            }
        if system == "linux" and shutil.which("apt-get") and hasattr(os, "geteuid") and os.geteuid() == 0:
            return {
                "git": ("apt-get", "install", "-y", "git"),
                "ffmpeg": ("apt-get", "install", "-y", "ffmpeg"),
            }
        return {}


    def bootstrap(profile: str = "recommended", execute: bool = True) -> dict[str, Any]:
        if profile not in {"core", "recommended"}:
            raise ValueError("profile must be core or recommended")
        commands = recommended_commands() if profile == "recommended" else {}
        results: list[InstallResult] = []
        for capability in ("git", "ffmpeg", "ollama"):
            if shutil.which(capability):
                results.append(InstallResult(capability, True, False, detail="already available"))
                continue
            command = commands.get(capability)
            if not command:
                results.append(InstallResult(capability, False, False, detail="no supported package manager; core remains usable"))
                continue
            if not execute:
                results.append(InstallResult(capability, False, False, command, "dry run"))
                continue
            process = subprocess.run(command, text=True, capture_output=True, timeout=1800, check=False)
            installed = process.returncode == 0
            detail = (process.stdout + process.stderr)[-2000:]
            results.append(InstallResult(capability, installed, True, command, detail))
        return {
            "profile": profile,
            "platform": platform.platform(),
            "core_ready": True,
            "results": [asdict(item) for item in results],
        }
    ''',
)

# Extend CLI with an explicit, auditable runtime bootstrap command.
cli = ROOT / "src/cinenode/cli.py"
source = cli.read_text(encoding="utf-8")
if "from .bootstrap import bootstrap as bootstrap_runtime" not in source:
    source = source.replace(
        "from .api.app import create_app\n",
        "from .api.app import create_app\nfrom .bootstrap import bootstrap as bootstrap_runtime\n",
    )
if '@app.command("bootstrap")' not in source:
    source += '''\n\n@app.command("bootstrap")\ndef bootstrap_command(\n    profile: str = typer.Option("recommended", help="core or recommended"),\n    dry_run: bool = typer.Option(False, "--dry-run"),\n) -> None:\n    result = bootstrap_runtime(profile=profile, execute=not dry_run)\n    typer.echo(json.dumps(result, indent=2, ensure_ascii=False))\n'''
cli.write_text(source, encoding="utf-8")

# Wire model manager into application services and API.
api = ROOT / "src/cinenode/api/app.py"
source = api.read_text(encoding="utf-8")
if "from cinenode.models import ModelManager" not in source:
    source = source.replace(
        "from cinenode.jobs import JobService\n",
        "from cinenode.jobs import JobService\nfrom cinenode.models import ModelManager\n",
    )
if "self.models = ModelManager" not in source:
    source = source.replace(
        "        self.backups = BackupService(settings, self.database)\n",
        "        self.backups = BackupService(settings, self.database)\n"
        "        manifest = Path(__file__).resolve().parents[1] / 'manifests' / 'models.json'\n"
        "        self.models = ModelManager(settings.models_dir, manifest)\n",
    )
if 'async def list_models()' not in source:
    marker = '    @app.get("/api/engines")\n'
    addition = '''    @app.get("/api/models")\n    async def list_models() -> list[dict[str, Any]]:\n        return services.models.list()\n\n    @app.post("/api/models/{model_id}/install")\n    async def install_model(model_id: str) -> dict[str, Any]:\n        try:\n            return await asyncio.to_thread(services.models.install, model_id)\n        except KeyError as exc:\n            raise HTTPException(404, str(exc)) from exc\n        except ValueError as exc:\n            raise HTTPException(422, str(exc)) from exc\n\n'''
    source = source.replace(marker, addition + marker)
api.write_text(source, encoding="utf-8")

# The web graph editor now supports actual port-to-port connections, undo and redo.
write(
    "src/cinenode/web/state.js",
    r'''
    export class State {
      constructor(){this.nodes=[];this.selected=null;this.workflow=null;this.listeners=new Set();this.undoStack=[];this.redoStack=[];}
      subscribe(listener){this.listeners.add(listener);return()=>this.listeners.delete(listener)}
      emit(){for(const listener of this.listeners)listener(this)}
      snapshot(){return JSON.stringify({nodes:this.nodes,selected:this.selected})}
      remember(){this.undoStack.push(this.snapshot());if(this.undoStack.length>100)this.undoStack.shift();this.redoStack=[];}
      restore(value){const parsed=JSON.parse(value);this.nodes=parsed.nodes;this.selected=parsed.selected;this.emit();}
      undo(){if(!this.undoStack.length)return;this.redoStack.push(this.snapshot());this.restore(this.undoStack.pop());}
      redo(){if(!this.redoStack.length)return;this.undoStack.push(this.snapshot());this.restore(this.redoStack.pop());}
      setWorkflow(item){this.workflow=item;this.nodes=structuredClone(item?.definition?.nodes||[]);this.selected=null;this.undoStack=[];this.redoStack=[];this.emit();}
      add(type,x=120,y=120){this.remember();let base=type.replace(/[^a-z0-9]/gi,"_");let id=base;let i=1;while(this.nodes.some(n=>n.id===id))id=`${base}_${i++}`;this.nodes.push({id,type,x,y,params:{},inputs:{}});this.selected=id;this.emit();}
      select(id){this.selected=id;this.emit();}
      remove(id){this.remember();this.nodes=this.nodes.filter(n=>n.id!==id);for(const node of this.nodes){for(const [name,binding] of Object.entries(node.inputs||{})){if(binding?.node===id)delete node.inputs[name];}}if(this.selected===id)this.selected=null;this.emit();}
      update(id,patch,{history=true}={}){const node=this.nodes.find(n=>n.id===id);if(!node)return;if(history)this.remember();Object.assign(node,patch);this.emit();}
      connect(source,target,inputName="input"){if(source===target)throw new Error("A node cannot connect to itself");const node=this.nodes.find(n=>n.id===target);if(!node)throw new Error("Target node not found");this.remember();node.inputs={...(node.inputs||{}),[inputName]:{node:source}};this.emit();}
      definition(){return {version:1,nodes:structuredClone(this.nodes)}}
    }
    ''',
)

write(
    "src/cinenode/web/canvas.js",
    r'''
    export class Canvas {
      constructor(root,state){this.root=root;this.nodeLayer=root.querySelector("#nodes");this.svg=root.querySelector("#connections");this.state=state;this.drag=null;this.connecting=null;state.subscribe(()=>this.render());this.bind();}
      bind(){
        this.root.addEventListener("pointermove",e=>{if(!this.drag)return;const rect=this.root.getBoundingClientRect();this.state.update(this.drag.id,{x:Math.max(0,e.clientX-rect.left-this.drag.dx),y:Math.max(0,e.clientY-rect.top-this.drag.dy)},{history:false});});
        window.addEventListener("pointerup",()=>{this.drag=null;this.connecting=null;});
        this.root.addEventListener("click",e=>{if(e.target===this.root)this.state.select(null);});
      }
      render(){
        this.nodeLayer.replaceChildren();
        for(const node of this.state.nodes){
          const el=document.createElement("div");el.className=`node${node.id===this.state.selected?" selected":""}`;el.style.transform=`translate(${node.x||0}px,${node.y||0}px)`;el.dataset.id=node.id;
          el.innerHTML=`<div class="node-head"></div><div class="node-type"></div><button class="port in" aria-label="input port"></button><button class="port out" aria-label="output port"></button>`;
          el.querySelector(".node-head").textContent=node.id;el.querySelector(".node-type").textContent=node.type;
          el.addEventListener("click",event=>{event.stopPropagation();this.state.select(node.id);});
          el.addEventListener("pointerdown",event=>{if(event.button!==0||event.target.classList.contains("port"))return;const rect=el.getBoundingClientRect();this.drag={id:node.id,dx:event.clientX-rect.left,dy:event.clientY-rect.top};});
          const output=el.querySelector(".port.out"),input=el.querySelector(".port.in");
          output.addEventListener("pointerdown",event=>{event.stopPropagation();this.connecting=node.id;});
          input.addEventListener("pointerup",event=>{event.stopPropagation();if(!this.connecting)return;const name=prompt("Target input name","input")||"input";try{this.state.connect(this.connecting,node.id,name);}catch(error){alert(error.message);}finally{this.connecting=null;}});
          this.nodeLayer.append(el);
        }
        this.drawEdges();
      }
      drawEdges(){
        this.svg.replaceChildren();
        for(const target of this.state.nodes){for(const binding of Object.values(target.inputs||{})){if(!binding||typeof binding!=="object"||!binding.node)continue;const source=this.state.nodes.find(n=>n.id===binding.node);if(!source)continue;const path=document.createElementNS("http://www.w3.org/2000/svg","path");const x1=(source.x||0)+190,y1=(source.y||0)+48,x2=(target.x||0),y2=(target.y||0)+48,c=Math.max(60,Math.abs(x2-x1)*.45);path.setAttribute("d",`M${x1},${y1} C${x1+c},${y1} ${x2-c},${y2} ${x2},${y2}`);path.setAttribute("fill","none");path.setAttribute("stroke","#7c5cff");path.setAttribute("stroke-width","2");this.svg.append(path);}}
      }
    }
    ''',
)

index = ROOT / "src/cinenode/web/index.html"
source = index.read_text(encoding="utf-8")
source = source.replace(
    '<button id="clearCanvas">Clear</button><span id="message"></span>',
    '<button id="undoCanvas" title="Undo">Undo</button><button id="redoCanvas" title="Redo">Redo</button><button id="clearCanvas">Clear</button><span id="message"></span>',
)
source = source.replace(
    '<label>Parameters<textarea id="nodeParams" rows="12"></textarea></label>',
    '<label>Parameters<textarea id="nodeParams" rows="8"></textarea></label><label>Input bindings<textarea id="nodeInputs" rows="8"></textarea></label>',
)
index.write_text(source, encoding="utf-8")

appjs = ROOT / "src/cinenode/web/app.js"
source = appjs.read_text(encoding="utf-8")
source = source.replace(
    '$("#nodeParams").value=JSON.stringify(node.params||{},null,2)',
    '$("#nodeParams").value=JSON.stringify(node.params||{},null,2);$("#nodeInputs").value=JSON.stringify(node.inputs||{},null,2)',
)
source = source.replace(
    'state.update(state.selected,{params:JSON.parse($("#nodeParams").value||"{}")});',
    'state.update(state.selected,{params:JSON.parse($("#nodeParams").value||"{}"),inputs:JSON.parse($("#nodeInputs").value||"{}")});',
)
if '$("#undoCanvas")' not in source:
    source = source.replace(
        '$("#clearCanvas").addEventListener',
        '$("#undoCanvas").addEventListener("click",()=>state.undo());$("#redoCanvas").addEventListener("click",()=>state.redo());$("#clearCanvas").addEventListener',
    )
appjs.write_text(source, encoding="utf-8")

styles = ROOT / "src/cinenode/web/styles.css"
source = styles.read_text(encoding="utf-8")
source = source.replace(
    '.port{position:absolute;width:10px;height:10px;border-radius:50%;background:var(--accent);top:48px}',
    '.port{position:absolute;width:14px;height:14px;padding:0;border-radius:50%;background:var(--accent);top:43px;z-index:3}',
)
source = source.replace('.port.in{left:-5px}.port.out{right:-5px}', '.port.in{left:-7px}.port.out{right:-7px}')
styles.write_text(source, encoding="utf-8")

# Launchers install core dependencies and attempt recommended system runtimes; failures do not hide the usable core.
write(
    "RUN_CINENODE.bat",
    r'''
    @echo off
    setlocal EnableExtensions
    cd /d "%~dp0"
    where py >nul 2>nul || (
      echo Python was not found. Installing Python 3.12 with winget...
      where winget >nul 2>nul || (echo Install Python 3.12 from python.org and run this file again.& pause & exit /b 1)
      winget install --id Python.Python.3.12 --exact --accept-package-agreements --accept-source-agreements || exit /b 1
    )
    if not exist ".venv\Scripts\python.exe" py -3.12 -m venv .venv || py -3 -m venv .venv || exit /b 1
    call ".venv\Scripts\activate.bat"
    python -m pip install --disable-pip-version-check -U pip setuptools wheel || exit /b 1
    python -m pip install -e . || exit /b 1
    if not "%CINENODE_SKIP_SYSTEM_BOOTSTRAP%"=="1" python -m cinenode bootstrap --profile recommended || echo Optional runtime bootstrap was not fully completed; CineNode core will still start.
    python -m cinenode serve --open
    ''',
)

write(
    "scripts/bootstrap_runtime.py",
    r'''
    from __future__ import annotations

    import argparse
    import json

    from cinenode.bootstrap import bootstrap


    parser = argparse.ArgumentParser(description="Install detected CineNode runtime dependencies")
    parser.add_argument("--profile", choices=("core", "recommended"), default="recommended")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    print(json.dumps(bootstrap(args.profile, execute=not args.dry_run), indent=2, ensure_ascii=False))
    ''',
)

# Optional dependency groups stay separate from the local-first core.
pyproject = ROOT / "pyproject.toml"
source = pyproject.read_text(encoding="utf-8")
if 'llama = ["llama-cpp-python' not in source:
    source = source.replace(
        '[project.optional-dependencies]\n',
        '[project.optional-dependencies]\nllama = ["llama-cpp-python>=0.3,<1"]\nvision = ["numpy>=2,<3", "Pillow>=10,<12", "opencv-python-headless>=4.10,<5", "onnxruntime>=1.20,<2"]\nmesh = ["numpy>=2,<3", "trimesh>=4.5,<5", "scipy>=1.14,<2"]\n',
    )
pyproject.write_text(source, encoding="utf-8")

write(
    "tests/test_models_bootstrap.py",
    r'''
    from pathlib import Path
    import hashlib
    import json

    import pytest

    from cinenode.bootstrap import bootstrap, recommended_commands
    from cinenode.engines.llama_cpp import LlamaCppEngine
    from cinenode.models import ModelManager, ModelSpec


    def test_model_spec_requires_https_hash_and_safe_name():
        valid = {
            "id": "demo.gguf",
            "name": "Demo",
            "filename": "demo.gguf",
            "url": "https://models.example.invalid/demo.gguf",
            "sha256": "a" * 64,
            "max_bytes": 100,
            "license": "TEST",
            "engine": "llama-cpp",
        }
        assert ModelSpec.from_dict(valid).id == "demo.gguf"
        for key, value in (("url", "http://example.invalid/model"), ("sha256", "bad"), ("filename", "../bad")):
            candidate = dict(valid)
            candidate[key] = value
            if key == "filename":
                # Path.name normalizes the destination; traversal never survives the contract.
                assert ModelSpec.from_dict(candidate).filename == "bad"
            else:
                with pytest.raises(ValueError):
                    ModelSpec.from_dict(candidate)


    def test_model_manager_reports_verified_local_file(tmp_path: Path):
        data = b"model-bytes"
        digest = hashlib.sha256(data).hexdigest()
        manifest = tmp_path / "models.json"
        manifest.write_text(json.dumps({"models": [{
            "id": "demo", "name": "Demo", "filename": "demo.gguf",
            "url": "https://models.example.invalid/demo.gguf", "sha256": digest,
            "max_bytes": 1024, "license": "TEST", "engine": "llama-cpp"
        }]}))
        root = tmp_path / "installed"
        target = root / "llama-cpp" / "demo.gguf"
        target.parent.mkdir(parents=True)
        target.write_bytes(data)
        manager = ModelManager(root, manifest)
        item = manager.list()[0]
        assert item["installed"] is True
        assert "url" not in item


    @pytest.mark.asyncio
    async def test_llama_cpp_probe_is_graceful_without_model():
        result = await LlamaCppEngine().probe()
        assert result["ok"] is False
        assert "model" in result


    def test_bootstrap_dry_run_never_executes_installers():
        result = bootstrap("recommended", execute=False)
        assert result["core_ready"] is True
        assert all(item["attempted"] is False for item in result["results"])
        assert isinstance(recommended_commands(), dict)
    ''',
)

write(
    "docs/ENGINES.md",
    r'''
    # Local inference engines

    CineNode does not lock workflows to one inference vendor. The core includes adapters for Ollama,
    OpenAI-compatible local servers (LM Studio/llama.cpp servers), ComfyUI and in-process
    `llama-cpp-python`. Engines run behind a small `EngineAdapter` contract and can be moved into
    other applications through Python entry points.

    `RUN_CINENODE.bat` installs the Python core and attempts to install Git, FFmpeg and Ollama with
    the operating system package manager when they are missing. Set
    `CINENODE_SKIP_SYSTEM_BOOTSTRAP=1` to disable those optional system changes. Large model weights
    are never silently downloaded: a model must be present in the reviewed manifest with license,
    immutable HTTPS URL, maximum size and expected SHA-256.

    ComfyUI and GPU-specific PyTorch builds remain external runtimes because CUDA/ROCm selection is
    hardware-specific. CineNode probes them and continues operating when they are unavailable.
    ''',
)

write(
    "docs/PATCH_LEVEL.json",
    json.dumps(
        {
            "product": "CineNode",
            "patch_level": 3,
            "contracts": [
                "runtime bootstrap is auditable and optional",
                "model downloads are manifest and checksum controlled",
                "llama.cpp can run in-process as an optional engine",
                "canvas creates and edits real graph connections",
                "undo and redo are available in the graph editor",
            ],
        },
        indent=2,
    )
    + "\n",
)

print("CineNode patch v3 applied")
