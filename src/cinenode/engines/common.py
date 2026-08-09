from __future__ import annotations

from urllib.parse import urlsplit
import ipaddress
import socket


def validate_engine_url(url: str, allow_private: bool = False) -> str:
    parsed=urlsplit(url)
    if parsed.scheme not in {"http","https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("engine URL must be plain http(s) without credentials")
    host=parsed.hostname
    if host in {"localhost","127.0.0.1","::1"}:
        return url.rstrip("/")
    addresses={item[4][0] for item in socket.getaddrinfo(host,parsed.port or (443 if parsed.scheme=="https" else 80),type=socket.SOCK_STREAM)}
    for value in addresses:
        ip=ipaddress.ip_address(value)
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved) and not allow_private:
            raise ValueError("private-network engine URL requires explicit permission")
    return url.rstrip("/")
