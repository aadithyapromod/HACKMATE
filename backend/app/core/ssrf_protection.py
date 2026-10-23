import ipaddress
import socket
from urllib.parse import urlparse
from typing import Tuple
from app.core.errors import HackMateException


class SSRFViolationError(HackMateException):
    def __init__(self, detail: str):
        super().__init__(f"SSRF Protection blocked request: {detail}", status_code=400)


# Blocked IP networks
BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),          # Current network
    ipaddress.ip_network("10.0.0.0/8"),         # RFC 1918 Private
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-local / Cloud Metadata
    ipaddress.ip_network("172.16.0.0/12"),      # RFC 1918 Private
    ipaddress.ip_network("192.168.0.0/16"),     # RFC 1918 Private
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved
    ipaddress.ip_network("255.255.255.255/32"), # Broadcast
    ipaddress.ip_network("::1/128"),            # IPv6 Loopback
    ipaddress.ip_network("fc00::/7"),           # IPv6 Unique Local
    ipaddress.ip_network("fe80::/10"),          # IPv6 Link-Local
]

BLOCKED_HOSTNAMES = {
    "localhost", "127.0.0.1", "::1", "metadata.google.internal",
    "instance-data", "metadata", "docker.internal", "host.docker.internal"
}


def validate_url_ssrf(url: str) -> Tuple[bool, str]:
    """
    Validates a URL against Server-Side Request Forgery (SSRF).
    Blocks non-HTTP/HTTPS protocols, loopbacks, private networks, and cloud metadata endpoints.
    Returns: (is_safe: bool, validated_url: str)
    """
    if not url or not isinstance(url, str):
        raise SSRFViolationError("URL must be a non-empty string.")

    parsed = urlparse(url.strip())

    # 1. Enforce scheme
    if parsed.scheme.lower() not in ("http", "https"):
        raise SSRFViolationError(f"Protocol '{parsed.scheme}' is forbidden. Only HTTP/HTTPS are permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFViolationError("URL does not contain a valid hostname.")

    hostname_lower = hostname.lower()

    # 2. Block reserved hostnames
    if hostname_lower in BLOCKED_HOSTNAMES or hostname_lower.endswith(".localhost") or hostname_lower.endswith(".internal"):
        raise SSRFViolationError(f"Hostname '{hostname}' resolves to a restricted local or internal domain.")

    # 3. DNS resolution and IP address range check
    try:
        addr_infos = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80), proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise SSRFViolationError(f"Unable to resolve hostname '{hostname}'.")

    resolved_ips = set()
    for family, _, _, _, sockaddr in addr_infos:
        ip_str = sockaddr[0]
        resolved_ips.add(ip_str)

    for ip_str in resolved_ips:
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            for net in BLOCKED_NETWORKS:
                if ip_obj in net:
                    raise SSRFViolationError(
                        f"Hostname '{hostname}' resolved to blocked private or metadata IP '{ip_str}'."
                    )
        except ValueError:
            raise SSRFViolationError(f"Invalid IP address format: '{ip_str}'.")

    return True, parsed.geturl()
