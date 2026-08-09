"""Devolve o software ao estado de fábrica, preservando o que custou caro.

O que APAGA: projetos, jobs, assets, snapshots, coleções, cache de nó, saídas,
uploads, logs e configuração do usuário.

O que PRESERVA, e por quê:
  - `data/models` (86 GB): pesos baixados. Apagar custaria horas de download e
    nada disso é "arquivo gerado" — é insumo.
  - `data/engines` (603 MB): binários compilados, mesmo motivo.
  - `data/backups`: é justamente o que torna o reset reversível.

Exige `--confirmar` porque o padrão de um script destrutivo tem de ser não fazer
nada. Sem backup recente na pasta, recusa — resetar sem rede de segurança é o
tipo de operação que só se descobre errada depois.

Uso:
    python scripts/resetar.py                # mostra o que faria
    python scripts/resetar.py --confirmar    # executa
"""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "data"

# Pastas cujo conteúdo é gerado e pode ser refeito.
PASTAS_LIMPAVEIS = ["outputs", "uploads", "logs", "tmp", "projects", "assets"]

# Preservadas por decisão explícita, não por esquecimento.
PASTAS_PRESERVADAS = {"models": "pesos baixados, insumo e não resultado",
                      "engines": "binários compilados",
                      "backups": "é o que torna este reset reversível"}

# Tabelas de conteúdo do usuário. `settings` e `governance_*` são recriadas pela
# semente no próximo boot, então também entram.
TABELAS = [
    "node_results", "asset_collection_items", "asset_collections",
    "project_snapshots", "assets", "jobs", "projects",
    "governance_alerts", "governance_audits", "governance_decisions",
    "governance_opensource", "governance_logs", "governance_changes",
    "governance_documents", "governance_tasks", "audit_events",
    "engine_checks", "settings",
]


def medir() -> dict[str, object]:
    """Inventário do que existe agora, para o relatório dizer o que some."""
    relatorio: dict[str, object] = {"pastas": {}, "tabelas": {}}
    for nome in PASTAS_LIMPAVEIS:
        pasta = DADOS / nome
        if not pasta.is_dir():
            relatorio["pastas"][nome] = {"arquivos": 0, "bytes": 0}
            continue
        arquivos = [f for f in pasta.rglob("*") if f.is_file()]
        relatorio["pastas"][nome] = {
            "arquivos": len(arquivos),
            "bytes": sum(f.stat().st_size for f in arquivos),
        }

    banco = DADOS / "cinenode.sqlite3"
    if banco.is_file():
        conexao = sqlite3.connect(f"file:{banco}?mode=ro", uri=True)
        try:
            for tabela in TABELAS:
                try:
                    relatorio["tabelas"][tabela] = conexao.execute(
                        f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
                except sqlite3.Error:
                    relatorio["tabelas"][tabela] = None
        finally:
            conexao.close()
    return relatorio


def backup_recente() -> Path | None:
    """O backup mais novo. Sem nenhum, o reset é irreversível e recusa."""
    pasta = DADOS / "backups"
    if not pasta.is_dir():
        return None
    zips = sorted(pasta.glob("*.zip"), key=lambda f: f.stat().st_mtime)
    return zips[-1] if zips else None


def servidor_no_ar() -> bool:
    """Resetar com o servidor rodando deixaria o processo com estado velho em
    memória e o banco vazio no disco — os dois discordando até o próximo boot."""
    import urllib.request

    try:
        with urllib.request.urlopen("http://127.0.0.1:8787/api/health", timeout=3):
            return True
    except Exception:      # noqa: BLE001 — qualquer falha significa fora do ar
        return False


def limpar_pastas() -> list[str]:
    feito = []
    for nome in PASTAS_LIMPAVEIS:
        pasta = DADOS / nome
        if not pasta.is_dir():
            continue
        removidos = 0
        for item in pasta.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)
            removidos += 1
        pasta.mkdir(exist_ok=True)
        feito.append(f"{nome}: {removidos} itens")
    return feito


def limpar_banco() -> list[str]:
    """Esvazia as tabelas em vez de apagar o arquivo.

    Apagar o `.sqlite3` funcionaria e perderia o histórico de migrações; o próximo
    boot reaplicaria as cinco do zero. Esvaziar mantém o esquema já migrado e a
    versão registrada, que é o estado correto de uma instalação nova e atual.
    """
    banco = DADOS / "cinenode.sqlite3"
    if not banco.is_file():
        return ["banco inexistente: nada a esvaziar"]

    conexao = sqlite3.connect(banco)
    feito = []
    try:
        conexao.execute("PRAGMA foreign_keys = OFF")
        for tabela in TABELAS:
            try:
                antes = conexao.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
                conexao.execute(f"DELETE FROM {tabela}")
                if antes:
                    feito.append(f"{tabela}: {antes} linhas")
            except sqlite3.Error as erro:
                feito.append(f"{tabela}: {erro}")
        conexao.commit()
        # VACUUM devolve o espaço ao disco; sem ele o arquivo continua do tamanho
        # que tinha cheio, e "resetado" com 900 KB confunde quem for conferir.
        conexao.execute("VACUUM")
    finally:
        conexao.close()
    return feito


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirmar", action="store_true",
                        help="executa de fato; sem isto apenas mostra o que faria")
    parser.add_argument("--sem-backup", action="store_true",
                        help="permite resetar sem backup na pasta (não recomendado)")
    args = parser.parse_args()

    relatorio = medir()
    total_arquivos = sum(p["arquivos"] for p in relatorio["pastas"].values())
    total_bytes = sum(p["bytes"] for p in relatorio["pastas"].values())
    total_linhas = sum(v for v in relatorio["tabelas"].values() if v)

    print("O QUE SERA APAGADO")
    for nome, dados in relatorio["pastas"].items():
        if dados["arquivos"]:
            print(f"  data/{nome:<12} {dados['arquivos']:>5} arquivos  "
                  f"{dados['bytes'] / 1e6:>8.1f} MB")
    for tabela, linhas in relatorio["tabelas"].items():
        if linhas:
            print(f"  tabela {tabela:<28} {linhas:>6} linhas")
    print(f"  TOTAL: {total_arquivos} arquivos, {total_bytes / 1e6:.1f} MB, "
          f"{total_linhas} linhas")

    print("\nO QUE SERA PRESERVADO")
    for nome, motivo in PASTAS_PRESERVADAS.items():
        pasta = DADOS / nome
        tamanho = sum(f.stat().st_size for f in pasta.rglob("*") if f.is_file()) if pasta.is_dir() else 0
        print(f"  data/{nome:<10} {tamanho / 1e9:>6.1f} GB  — {motivo}")

    if not args.confirmar:
        print("\nNada foi alterado. Para executar: python scripts/resetar.py --confirmar")
        return 0

    if servidor_no_ar():
        print("\nRECUSADO: o servidor está no ar em 127.0.0.1:8787.")
        print("Resetar agora deixaria o processo com estado velho em memória e o")
        print("banco vazio no disco. Pare com: LIGAR.bat /desligar")
        return 2

    backup = backup_recente()
    if backup is None and not args.sem_backup:
        print("\nRECUSADO: não há backup em data/backups.")
        print("Crie um em Configurações > Criar backup completo, ou use --sem-backup.")
        return 2
    if backup:
        print(f"\nbackup mais recente: {backup.name} ({backup.stat().st_size / 1e6:.1f} MB)")

    print("\nEXECUTANDO")
    for linha in limpar_pastas():
        print(f"  pasta {linha}")
    for linha in limpar_banco():
        print(f"  {linha}")

    print("\nReset concluído. O proximo boot recria a semente de governanca, os")
    print("perfis de modelo padrao e as pastas vazias.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
