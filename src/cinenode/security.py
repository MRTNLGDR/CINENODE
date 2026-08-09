from __future__ import annotations

import ipaddress
import socket
from pathlib import Path
from urllib.parse import urlparse


LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1", "testserver", "testclient"}


def is_loopback_host(host: str | None) -> bool:
    if not host:
        return False
    value = host.split(":", 1)[0].strip("[]").lower()
    if value in LOOPBACK_HOSTS:
        return True
    try:
        return ipaddress.ip_address(value).is_loopback
    except ValueError:
        return False


def require_local_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("URL HTTP(S) inválida")
    if parsed.username or parsed.password:
        raise ValueError("Credenciais embutidas na URL não são permitidas")
    host = parsed.hostname.lower()
    if host == "localhost":
        return url
    try:
        infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError(f"Host não resolvido: {host}") from exc
    addresses = {item[4][0] for item in infos}
    if not addresses or any(not ipaddress.ip_address(address).is_loopback for address in addresses):
        raise ValueError("CineNode só permite sidecars HTTP no loopback")
    return url


def safe_child(root: Path, candidate: str | Path) -> Path:
    base = root.resolve()
    path = Path(candidate)
    resolved = (base / path).resolve() if not path.is_absolute() else path.resolve()
    if resolved != base and base not in resolved.parents:
        raise ValueError("Caminho fora do workspace CineNode")
    return resolved
