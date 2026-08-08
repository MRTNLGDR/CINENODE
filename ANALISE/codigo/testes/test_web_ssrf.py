"""SEC-005: o navegador interno não pode virar porta para a rede local.

Sem esta guarda, `POST /api/web/fetch` com `http://127.0.0.1:11434` faria o servidor
ler o Ollama e devolver o conteúdo ao cliente — e o mesmo vale para o metadata de
nuvem em `169.254.169.254` e para qualquer serviço na faixa privada.
"""
from __future__ import annotations

import pytest

from cinenode.api import _endereco_permitido, _resolver_destino_publico


# ---- o que precisa ser recusado ---------------------------------------------

@pytest.mark.parametrize("host", [
    "127.0.0.1",          # loopback: o próprio servidor e os sidecars
    "localhost",
    "0.0.0.0",
    "169.254.169.254",    # metadata de nuvem
    "10.0.0.1",           # privada classe A
    "172.16.0.1",         # privada classe B
    "192.168.1.1",        # privada classe C
    "::1",                # loopback IPv6
    "224.0.0.1",          # multicast
])
def test_endereco_interno_e_recusado(host):
    permitido, motivo = _endereco_permitido(host)
    assert permitido is False, f"{host} deveria ser recusado"
    assert motivo, "recusa sem motivo não ensina nada"


def test_esquema_nao_http_e_recusado():
    for url in ("file:///C:/Windows/System32/drivers/etc/hosts",
                "ftp://exemplo.com/x",
                "gopher://127.0.0.1:11434"):
        permitido, motivo = _resolver_destino_publico(url)
        assert permitido is False, url
        assert "esquema" in motivo or "host" in motivo


def test_url_sem_host_e_recusada():
    permitido, motivo = _resolver_destino_publico("http://")
    assert permitido is False
    assert "host" in motivo


def test_host_inexistente_e_recusado_sem_travar():
    """DNS que não resolve devolve recusa com o motivo, não exceção."""
    permitido, motivo = _endereco_permitido("host-que-nao-existe.invalid")
    assert permitido is False
    assert "resolver" in motivo


def test_ollama_local_nao_e_alcancavel_pelo_navegador():
    """Caso concreto: o Ollama roda em 11434 e não pode ser lido por esta rota."""
    permitido, _ = _resolver_destino_publico("http://127.0.0.1:11434/api/tags")
    assert permitido is False


def test_comfyui_local_nao_e_alcancavel():
    permitido, _ = _resolver_destino_publico("http://127.0.0.1:8188/system_stats")
    assert permitido is False


def test_o_proprio_cinenode_nao_e_alcancavel():
    """Sem isto, a rota poderia ler a própria API e vazar settings."""
    permitido, _ = _resolver_destino_publico("http://127.0.0.1:8787/api/settings")
    assert permitido is False


# ---- o que precisa continuar passando ---------------------------------------

def test_dominio_publico_e_permitido():
    """Portão que bloqueia navegação legítima é desligado, e aí nunca serviu."""
    permitido, motivo = _resolver_destino_publico("https://example.com")
    assert permitido is True, motivo


def test_https_e_http_publicos_sao_permitidos():
    for url in ("http://example.com", "https://example.com/caminho?q=1"):
        permitido, motivo = _resolver_destino_publico(url)
        assert permitido is True, f"{url}: {motivo}"


# ---- limites declarados -----------------------------------------------------

def test_limites_existem_e_sao_conservadores():
    from cinenode.api import _MAX_BYTES_WEB, _MAX_REDIRECIONAMENTOS

    assert _MAX_BYTES_WEB <= 32 * 1024 * 1024, "limite alto demais vira DoS de memória"
    assert 1 <= _MAX_REDIRECIONAMENTOS <= 5, "cadeia longa de redirecionamento é abuso"
