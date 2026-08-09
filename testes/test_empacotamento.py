"""O pacote precisa ser instalável, não só executável na máquina de quem escreveu.

Estes testes nasceram de um defeito real: o script de commit automático gravou
`pyproject.toml` com BOM (`Set-Content -Encoding UTF8` do PowerShell 5.1 sempre
adiciona BOM), o `tomllib` passou a recusar o arquivo, e `pip install` quebrou —
enquanto o servidor continuava rodando do pacote antigo. Ninguém percebeu porque
nada testava o empacotamento.
"""
from __future__ import annotations

import pathlib
import re
import tomllib

RAIZ = pathlib.Path(__file__).resolve().parents[1]

# Arquivos que quebram se ganharem BOM.
SEM_BOM = [
    "source/backend/pyproject.toml",
    "source/backend/cinenode/__init__.py",
    "source/frontend/app.js",
    "source/frontend/styles.css",
    "source/frontend/index.html",
]

# PowerShell 5.1 lê .ps1 sem BOM como Windows-1252 e quebra o parser nos acentos.
COM_BOM_SE_TIVER_ACENTO = list((RAIZ / "scripts").glob("*.ps1"))


def test_pyproject_e_toml_valido():
    caminho = RAIZ / "source/backend/pyproject.toml"
    texto = caminho.read_text(encoding="utf-8")
    # Escape, nunca o caractere literal: U+FEFF cru no fonte é exatamente o que a
    # auditoria de supply chain caça, e ela está certa em caçar.
    assert not texto.startswith("\ufeff"), "pyproject.toml com BOM: pip install falha"
    dados = tomllib.loads(texto)
    assert dados["project"]["name"]
    assert dados["project"]["version"]


def test_arquivos_de_codigo_nao_tem_bom():
    com_bom = [
        alvo for alvo in SEM_BOM
        if (RAIZ / alvo).exists() and (RAIZ / alvo).read_bytes().startswith(b"\xef\xbb\xbf")
    ]
    assert not com_bom, f"BOM quebra o parser destes arquivos: {com_bom}"


def test_scripts_powershell_com_acento_tem_bom():
    """Sem BOM, o PS 5.1 lê como ANSI e reporta o erro a 50 linhas do problema real."""
    faltando = []
    for script in COM_BOM_SE_TIVER_ACENTO:
        dados = script.read_bytes()
        tem_acento = any(byte > 127 for byte in dados)
        if tem_acento and not dados.startswith(b"\xef\xbb\xbf"):
            faltando.append(script.name)
    assert not faltando, f".ps1 com acento e sem BOM: {faltando}"


def test_versao_e_a_mesma_nos_dois_lugares():
    """Versão divergente entre o código e o pacote gera tag apontando para o nada."""
    init = (RAIZ / "source/backend/cinenode/__init__.py").read_text(encoding="utf-8")
    pyproject = tomllib.loads((RAIZ / "source/backend/pyproject.toml").read_text(encoding="utf-8"))
    match = re.search(r'__version__\s*=\s*"([^"]+)"', init)
    assert match, "__init__.py sem __version__"
    assert match.group(1) == pyproject["project"]["version"], (
        f"__init__.py diz {match.group(1)}, pyproject diz {pyproject['project']['version']}"
    )


def test_frontend_empacotado_esta_sincronizado():
    """O pacote serve `cinenode/frontend`; se ele ficar velho, a tela mostra a versão antiga."""
    divergentes = []
    for nome in ("app.js", "styles.css", "index.html"):
        fonte = RAIZ / "source/frontend" / nome
        embutido = RAIZ / "source/backend/cinenode/frontend" / nome
        if not fonte.exists() or not embutido.exists():
            continue
        if fonte.read_bytes() != embutido.read_bytes():
            divergentes.append(nome)
    assert not divergentes, (
        f"frontend embutido desatualizado: {divergentes}. "
        "Copie source/frontend/* para source/backend/cinenode/frontend/ antes de empacotar."
    )


def test_index_html_referencia_os_assets_sem_versao_fixa():
    """O carimbo de versão é aplicado pelo servidor; no arquivo ele não pode estar fixo."""
    html = (RAIZ / "source/frontend/index.html").read_text(encoding="utf-8")
    assert 'src="/app.js"' in html, "o servidor espera este literal para carimbar a versão"
    assert 'href="/styles.css"' in html
    assert "?v=" not in html, "versão fixa no HTML anula o cache-busting dinâmico"


def test_api_nao_tem_versao_literal():
    """Versão literal na API mente assim que o pacote sobe; a fonte é `__version__`."""
    api = (RAIZ / "source/backend/cinenode/api.py").read_text(encoding="utf-8")
    literais = re.findall(r'"version": "\d+\.\d+\.\d+"', api)
    assert not literais, f"versão fixa na API: {literais}"


def test_nenhum_arquivo_de_teste_esta_vazio():
    """Arquivo de teste sem teste é regressão de cobertura silenciosa.

    Conta `def test_` E `async def test_`: contar só o primeiro produziu um achado
    falso de auditoria, afirmando que dois arquivos com 7 testes reais estavam vazios.
    """
    vazios = []
    for arquivo in (RAIZ / "tests").glob("test_*.py"):
        texto = arquivo.read_text(encoding="utf-8")
        total = len(re.findall(r"^\s*(?:async\s+)?def test_", texto, re.M))
        if total == 0:
            vazios.append(arquivo.name)
    assert not vazios, f"arquivos de teste sem nenhum teste: {vazios}"
