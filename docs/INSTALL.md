# Instalação e diagnóstico

## Núcleo

O núcleo exige Python 3.11, 3.12 ou 3.13. Python 3.12 é a versão recomendada para compatibilidade ampla com bibliotecas de mídia.

```powershell
.\INSTALL_CINENODE.bat
.\RUN_CINENODE.bat
```

## Engines opcionais

```powershell
.\INSTALL_CINENODE.bat -WithEngines
```

O instalador tenta usar `winget` para Python, Git, FFmpeg e Ollama. O ComfyUI é clonado em `runtime/engines/ComfyUI` e usa uma `.venv` própria, isolada do núcleo; nenhum checkpoint é incluído.

## Diagnóstico

```powershell
.\.venv\Scripts\python.exe -m cinenode doctor
```

O relatório informa paths, banco e disponibilidade de sidecars/binários.
