WINDOWS
1. Extraia o arquivo ZIP.
2. Execute `run.bat`.
3. Aguarde a instalação automática do núcleo local.
4. A interface será aberta em `http://127.0.0.1:8787`.

> Este pacote contém o código e o inicializador de um clique. `Setup.exe/MSI` deve ser compilado no próprio Windows com `scripts/build-tauri.ps1 -Clean`; ele não foi inventado nem incluído sem build real.

MACOS
1. Extraia o ZIP.
2. Execute `install.command` ou `run.command`.
3. Confirme permissões quando solicitado.
4. A interface será aberta localmente.

> O `.dmg` depende do build Tauri em macOS e não está presente nesta entrega fonte.

LINUX
1. Extraia o ZIP.
2. Execute `./install.sh` ou `./run.sh`.
3. O aplicativo será iniciado localmente.

> AppImage/`.deb` dependem do build Tauri no sistema-alvo e não foram simulados.

# Engines e modelos no Alienware

No Windows PowerShell:

```powershell
.\scripts\bootstrap-opensources.ps1
.\scripts\install-engines.ps1 -Core -WithLLM -WithOpenCode
$env:HF_TOKEN="seu_token_somente_se_necessario"
.\scripts\download-models.ps1 -Bundle recommended
.\run.bat
```

O bootstrap clona commits exatos em quarentena, executa a auditoria de supply chain, gera checksums e só então promove o upstream ao acervo `Avangard One/opensources/upstream/`.

# Verificação

```powershell
python scripts\validate_package.py --root . --run-smoke
python scripts\model_manager.py list
```

A aplicação abre sem pesos para criar, salvar e validar workflows. Nós de inferência sem binário/peso falham com erro acionável; não retornam imagem ou vídeo falso.
