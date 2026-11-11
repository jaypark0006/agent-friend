"""Zero-dependency device discovery and HTTP transport for ESP-Mosaico 2.0.

Discovery order:
1. Explicit IP/host argument or `MOSAICO_IP` / `AGENT_FRIEND_IP` environment variable
2. `mosaico.local` mDNS resolution (OS resolver + raw UDP 5353 multicast fallback)
3. SSDP multicast `M-SEARCH` (`239.255.255.250:1900`, `urn:mosaico:device:screen:1`)
4. Local cached address (`~/.agent-friend/device.json` & `~/.cache/mosaico-notify/address.json`)
5. ARP table neighbor verification (`arp -an` / `/proc/net/arp`)
"""

from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass
import datetime
import ipaddress
import json
import os
from pathlib import Path
import re
import shutil
import socket
import struct
import subprocess
import tempfile
import time
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

MAX_HTTP_RESPONSE_BYTES = 1024 * 1024
AGENT_FRIEND_CACHE = Path.home() / ".agent-friend" / "device.json"
LEGACY_NOTIFY_CACHE = Path.home() / ".cache" / "mosaico-notify" / "address.json"


def utf8_clip(value: Any, max_bytes: int, max_chars: int | None = None) -> str:
    """Safely truncate text to `max_bytes` UTF-8 bytes without splitting codepoints."""
    text = str(value or "")
    if max_chars is not None:
        text = text[:max_chars]
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode("utf-8", errors="ignore")


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


_DIRECT_OPENER = urllib.request.build_opener(
    urllib.request.ProxyHandler({}),
    _NoRedirectHandler(),
)


@dataclass(frozen=True)
class DeviceEndpoint:
    """Resolved network address of an ESP-Mosaico companion screen."""

    host: str
    port: int = 80
    version: str = ""
    source: str = ""

    @property
    def authority(self) -> str:
        h = f"[{self.host}]" if ":" in self.host and not self.host.startswith("[") else self.host
        return h if self.port == 80 else f"{h}:{self.port}"

    @property
    def http_base(self) -> str:
        return f"http://{self.authority}"

    @property
    def ws_hub_url(self) -> str:
        return f"ws://{self.authority}/ws/hub"


def parse_host_port(raw: str, default_port: int = 80) -> tuple[str, int]:
    """Parse `'192.168.5.92'`, `'127.0.0.1:18080'`, or `'http://mosaico.local/...'`."""
    cleaned = raw.strip()
    if not cleaned:
        raise ValueError("Empty host string")
    if "://" in cleaned:
        parsed = urllib.parse.urlsplit(cleaned)
        if not parsed.hostname:
            raise ValueError(f"Invalid URL: {raw}")
        return parsed.hostname, parsed.port or default_port
    if cleaned.startswith("["):
        match = re.match(r"^\[([^\]]+)\](?::(\d+))?$", cleaned)
        if not match:
            raise ValueError(f"Invalid bracketed IPv6 address: {raw}")
        return match.group(1), int(match.group(2)) if match.group(2) else default_port
    if cleaned.count(":") == 1:
        host_part, port_part = cleaned.rsplit(":", 1)
        if port_part.isdigit():
            return host_part.strip(), int(port_part)
    return cleaned, default_port


def _validate_connectable_host(host: str) -> str:
    """Allow IP literals or clean RFC-1123 / `.local` hostnames; block URL injection."""
    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        pass
    if re.match(r"^[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$", host):
        return host
    raise ValueError(f"Disallowed host identifier: {host!r}")


def http_request(
    host: str,
    path: str,
    body: dict[str, Any] | bytes | None = None,
    *,
    port: int = 80,
    mime: str = "application/json",
    timeout: float = 3.0,
    raw: bool = False,
    method: str | None = None,
) -> Any:
    """Perform a proxy-free, redirect-free HTTP request to an ESP-Mosaico device."""
    safe_host = _validate_connectable_host(host)
    authority = f"[{safe_host}]" if ":" in safe_host else safe_host
    if port != 80:
        authority = f"{authority}:{port}"
    if not path.startswith("/"):
        path = "/" + path

    payload: bytes | None
    if isinstance(body, dict):
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    else:
        payload = body

    http_method = method or ("GET" if payload is None else "POST")
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = mime

    req = urllib.request.Request(
        f"http://{authority}{path}",
        data=payload,
        headers=headers,
        method=http_method,
    )
    with _DIRECT_OPENER.open(req, timeout=timeout) as resp:
        data = resp.read(MAX_HTTP_RESPONSE_BYTES + 1)
    if len(data) > MAX_HTTP_RESPONSE_BYTES:
        raise ValueError("Device HTTP response exceeded 1 MiB safety limit")
    if raw:
        return data
    if not data:
        return {}
    return json.loads(data.decode("utf-8", errors="replace"))


def _read_arp_mac_map() -> dict[str, str]:
    """Return `{ip: normalized_mac}` from OS ARP cache (`arp -an` or `/proc/net/arp`)."""
    result: dict[str, str] = {}
    proc_arp = Path("/proc/net/arp")
    if proc_arp.exists():
        try:
            for line in proc_arp.read_text(encoding="utf-8", errors="ignore").splitlines()[1:]:
                cols = line.split()
                if len(cols) >= 4 and re.match(r"^\d+\.\d+\.\d+\.\d+$", cols[0]):
                    mac = cols[3].lower()
                    if mac != "00:00:00:00:00:00" and len(mac.split(":")) == 6:
                        result[cols[0]] = ":".join(part.zfill(2) for part in mac.split(":"))
        except OSError:
            pass

    arp_bin = shutil.which("arp") or ("/usr/sbin/arp" if Path("/usr/sbin/arp").exists() else None)
    if arp_bin:
        try:
            out = subprocess.run(
                [arp_bin, "-an"],
                capture_output=True,
                text=True,
                timeout=2.0,
                check=False,
            ).stdout
            for ip, mac in re.findall(r"\(?(\d+\.\d+\.\d+\.\d+)\)?\s+at\s+([0-9A-Fa-f:.-]+)", out):
                parts = mac.replace("-", ":").split(":")
                if len(parts) == 6:
                    result[ip] = ":".join(p.zfill(2).lower() for p in parts)
        except (OSError, subprocess.TimeoutExpired):
            pass
    return result


def identify_device(
    host: str,
    port: int = 80,
    *,
    timeout: float = 1.5,
    expected_mac: str | None = None,
    arp_map: dict[str, str] | None = None,
    source: str = "",
) -> DeviceEndpoint | None:
    """Verify `GET /api/status` confirms `app == 'lan_screen'` (and optional MAC match)."""
    try:
        resolved_host, resolved_port = parse_host_port(host, default_port=port)
        info = http_request(resolved_host, "/api/status", port=resolved_port, timeout=timeout)
        if not isinstance(info, dict) or info.get("app") != "lan_screen":
            return None
        reported_ip = info.get("ip")
        connect_ip = resolved_host
        # If queried via mosaico.local, resolve to concrete IPv4 if device reported one or OS resolves it.
        if resolved_host.endswith(".local") and isinstance(reported_ip, str) and reported_ip:
            try:
                ipaddress.ip_address(reported_ip)
                connect_ip = reported_ip
            except ValueError:
                pass
        if expected_mac:
            mac_table = arp_map if arp_map is not None else _read_arp_mac_map()
            neighbor_mac = mac_table.get(connect_ip)
            if neighbor_mac and neighbor_mac.lower() != expected_mac.lower():
                return None
        return DeviceEndpoint(
            host=connect_ip,
            port=resolved_port,
            version=str(info.get("version") or ""),
            source=source,
        )
    except Exception:
        return None


def _mdns_udp_query(hostname: str = "mosaico.local", timeout: float = 0.6) -> list[str]:
    """Zero-dependency mDNS (`224.0.0.251:5353`) A-record query fallback."""
    labels = [lbl.encode("ascii") for lbl in hostname.rstrip(".").split(".") if lbl]
    qname = b"".join(bytes([len(lbl)]) + lbl for lbl in labels) + b"\x00"
    # Standard DNS header: ID=0, Flags=0, QDCOUNT=1, AN/NS/AR=0; QTYPE=A(1), QCLASS=IN(1) unicast-response bit
    packet = struct.pack("!HHHHHH", 0, 0, 1, 0, 0, 0) + qname + struct.pack("!HH", 1, 0x8001)
    found: list[str] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(timeout)
            sock.sendto(packet, ("224.0.0.251", 5353))
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                sock.settimeout(max(0.02, deadline - time.monotonic()))
                try:
                    resp, (src_ip, _) = sock.recvfrom(2048)
                except (socket.timeout, OSError):
                    break
                if len(resp) >= 12 and b"mosaico" in resp.lower():
                    # Check trailing 4 bytes for A-record or sender IP
                    if src_ip:
                        found.append(src_ip)
    except OSError:
        pass
    return list(dict.fromkeys(found))


def resolve_mdns_candidates(hostname: str = "mosaico.local", port: int = 80, timeout: float = 0.8) -> list[str]:
    """Resolve `mosaico.local` via OS getaddrinfo (bounded by thread timeout) + UDP mDNS."""
    results: list[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(socket.getaddrinfo, hostname, port, socket.AF_INET, socket.SOCK_STREAM)
        try:
            infos = fut.result(timeout=timeout)
            for item in infos:
                sockaddr = item[4]
                if sockaddr and isinstance(sockaddr[0], str):
                    results.append(sockaddr[0])
        except Exception:
            pass
    if not results:
        results.extend(_mdns_udp_query(hostname, timeout=min(0.5, timeout)))
    return list(dict.fromkeys(results))


def ssdp_discover_candidates(timeout: float = 0.6) -> list[tuple[str, int]]:
    """Send SSDP M-SEARCH multicast probes and return `[(host, port), ...]` candidates."""
    queries = (
        "M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\n"
        'MAN: "ssdp:discover"\r\nMX: 1\r\nST: urn:mosaico:device:screen:1\r\n\r\n',
        "M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\n"
        'MAN: "ssdp:discover"\r\nMX: 1\r\nST: ssdp:all\r\n\r\n',
    )
    candidates: list[tuple[str, int]] = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            for q in queries:
                try:
                    sock.sendto(q.encode("ascii"), ("239.255.255.250", 1900))
                except OSError:
                    pass
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                sock.settimeout(max(0.02, deadline - time.monotonic()))
                try:
                    data, (src_addr, _) = sock.recvfrom(4096)
                except (socket.timeout, OSError):
                    break
                text = data.decode("utf-8", errors="ignore")
                lowered = text.lower()
                if "mosaico" in lowered or "lan_screen" in lowered or "4553502d-4952-4953" in lowered:
                    loc = re.search(r"(?im)^location:\s*(\S+)", text)
                    if loc:
                        parsed = urllib.parse.urlsplit(loc.group(1).strip())
                        if parsed.hostname:
                            candidates.append((parsed.hostname, parsed.port or 80))
                            continue
                    if src_addr:
                        candidates.append((src_addr, 80))
    except OSError:
        pass
    return list(dict.fromkeys(candidates))


def load_cached_addresses() -> list[tuple[str, int]]:
    """Read cached device IP from `~/.agent-friend/device.json` and legacy notify cache."""
    entries: list[tuple[str, int]] = []
    for path in (AGENT_FRIEND_CACHE, LEGACY_NOTIFY_CACHE):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            ip = data.get("ip")
            port = int(data.get("port") or 80)
            if isinstance(ip, str) and ip.strip():
                h, p = parse_host_port(ip, default_port=port)
                entries.append((h, p))
        except Exception:
            continue
    return list(dict.fromkeys(entries))


def save_cached_endpoint(endpoint: DeviceEndpoint, expected_mac: str | None = None) -> None:
    """Atomically persist discovered device endpoint to `~/.agent-friend/device.json`."""
    payload = {
        "ip": endpoint.host,
        "port": endpoint.port,
        "version": endpoint.version,
        "mac": expected_mac,
        "updated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    for cache_path in (AGENT_FRIEND_CACHE, LEGACY_NOTIFY_CACHE):
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp_name = tempfile.mkstemp(prefix=".mosaico-mcp-", dir=str(cache_path.parent))
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    json.dump(payload, fh, ensure_ascii=False, indent=2)
                    fh.write("\n")
                os.replace(tmp_name, cache_path)
            finally:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
        except OSError:
            continue


def discover_device(
    explicit_ip: str | None = None,
    explicit_port: int | None = None,
    *,
    allow_network_scan: bool = True,
    persist_cache: bool = True,
) -> DeviceEndpoint | None:
    """Discover an ESP-Mosaico screen in priority order:
    `MOSAICO_IP` -> `mosaico.local` mDNS -> SSDP -> Local Cache -> ARP neighbors.
    """
    env_port_str = os.environ.get("MOSAICO_PORT", "").strip()
    default_port = explicit_port or (int(env_port_str) if env_port_str.isdigit() else 80)
    expected_mac = (os.environ.get("MOSAICO_MAC") or os.environ.get("AGENT_FRIEND_MAC") or "").strip().lower() or None

    tried: set[tuple[str, int]] = set()
    arp_cache: dict[str, str] | None = None

    def try_candidate(host_raw: str, port_val: int, source: str, timeout: float = 1.5) -> DeviceEndpoint | None:
        nonlocal arp_cache
        try:
            h, p = parse_host_port(host_raw, default_port=port_val)
        except ValueError:
            return None
        if (h, p) in tried:
            return None
        tried.add((h, p))
        if expected_mac and arp_cache is None:
            arp_cache = _read_arp_mac_map()
        ep = identify_device(h, p, timeout=timeout, expected_mac=expected_mac, arp_map=arp_cache, source=source)
        if ep and persist_cache:
            save_cached_endpoint(ep, expected_mac=expected_mac)
        return ep

    # 1. Explicit IP or MOSAICO_IP / AGENT_FRIEND_IP env var
    for raw_val, src in (
        (explicit_ip, "explicit"),
        (os.environ.get("MOSAICO_IP"), "env:MOSAICO_IP"),
        (os.environ.get("AGENT_FRIEND_IP"), "env:AGENT_FRIEND_IP"),
    ):
        if raw_val and raw_val.strip():
            ep = try_candidate(raw_val.strip(), default_port, src, timeout=2.0)
            if ep:
                return ep
            # If an explicit override was supplied and unreachable, do not silently talk to a different device.
            if src == "explicit":
                return None

    if not allow_network_scan:
        return None

    # 2. mosaico.local mDNS resolution
    for mdns_ip in resolve_mdns_candidates("mosaico.local", port=default_port, timeout=0.7):
        ep = try_candidate(mdns_ip, default_port, "mdns:mosaico.local", timeout=1.5)
        if ep:
            return ep

    # 3. SSDP multicast discovery
    for ssdp_host, ssdp_port in ssdp_discover_candidates(timeout=0.55):
        ep = try_candidate(ssdp_host, ssdp_port, "ssdp", timeout=1.5)
        if ep:
            return ep

    # 4. Local address cache
    for cached_host, cached_port in load_cached_addresses():
        ep = try_candidate(cached_host, cached_port, "cache", timeout=1.5)
        if ep:
            return ep

    # 5. ARP table neighbor verification
    arp_cache = _read_arp_mac_map()
    if expected_mac:
        arp_ips = [ip for ip, mac in arp_cache.items() if mac.lower() == expected_mac]
    else:
        arp_ips = list(arp_cache.keys())
    untried = [ip for ip in arp_ips if (ip, default_port) not in tried]
    if untried:
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            futures = [
                pool.submit(
                    identify_device,
                    ip,
                    default_port,
                    timeout=1.2,
                    expected_mac=expected_mac,
                    arp_map=arp_cache,
                    source="arp",
                )
                for ip in untried
            ]
            for fut in concurrent.futures.as_completed(futures):
                ep = fut.result()
                if ep:
                    if persist_cache:
                        save_cached_endpoint(ep, expected_mac=expected_mac)
                    return ep

    return None
