"""Command-line entry point for `mosaico-mcp` (`uvx --from ./mcp mosaico-mcp` / `python3 -m mosaico_mcp`)."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .client import MosaicoClient
from .discovery import discover_device
from .server import MosaicoMCPServer


def _run_doctor(ip: str | None, port: int | None) -> int:
    ep = discover_device(explicit_ip=ip, explicit_port=port, allow_network_scan=True)
    report: dict[str, object] = {
        "mcp_server": "mosaico-mcp",
        "version": __version__,
        "discovered": ep is not None,
    }
    if ep is not None:
        client = MosaicoClient(explicit_ip=ep.host, explicit_port=ep.port, allow_network_scan=False)
        try:
            ws_ok = client.hub.ensure_connected(ep.host, ep.port, timeout=2.5)
            report.update(
                {
                    "device_ip": ep.host,
                    "port": ep.port,
                    "firmware_version": ep.version,
                    "discovery_source": ep.source,
                    "http_base": ep.http_base,
                    "ws_hub_url": ep.ws_hub_url,
                    "ws_hub_connected": ws_ok,
                    "streamable_http_mcp": f"{ep.http_base}/mcp",
                }
            )
        finally:
            client.close()
    else:
        report["hint"] = (
            "未在当前局域网发现随身屏；插入电源联网后将自动通过 mosaico.local / SSDP / ARP 发现，"
            "也可通过环境变量 MOSAICO_IP 指定地址。"
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ep is not None else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mosaico-mcp",
        description="Official zero-dependency MCP Server (stdio) for ESP-Mosaico (Agent Friend) 2.0",
    )
    parser.add_argument("--ip", default=None, help="Optional ESP-Mosaico IP or host:port override")
    parser.add_argument("--port", type=int, default=None, help="Optional HTTP/WS port override (default: 80)")
    parser.add_argument("--doctor", action="store_true", help="Run LAN discovery & /ws/hub connectivity check and exit")
    parser.add_argument("--no-warmup", action="store_true", help="Disable background discovery warmup on startup")
    parser.add_argument("--version", action="version", version=f"mosaico-mcp {__version__}")

    args = parser.parse_args(argv)
    if args.doctor:
        return _run_doctor(args.ip, args.port)

    server = MosaicoMCPServer(
        explicit_ip=args.ip,
        explicit_port=args.port,
        background_warmup=not args.no_warmup,
    )
    return server.serve_forever()


if __name__ == "__main__":
    sys.exit(main())
