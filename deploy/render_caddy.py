"""Render the retained IP-HTTPS Caddy boundary for a validated public IPv4."""

from __future__ import annotations

import argparse
import ipaddress
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ip", required=True)
    args = parser.parse_args()
    address = ipaddress.ip_address(args.ip)
    if address.version != 4 or not address.is_global:
        raise SystemExit("public_ipv4_required")
    source = args.template.read_text(encoding="utf-8")
    if source.count("__PUBLIC_IP__") < 1:
        raise SystemExit("caddy_template_placeholder_missing")
    args.output.write_text(source.replace("__PUBLIC_IP__", str(address)), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
