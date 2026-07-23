from __future__ import annotations

import re
import sys


PORT_PATTERN = re.compile(r"[0-9]{1,5}")


def normalize_deploy_port(value: str) -> str:
    if PORT_PATTERN.fullmatch(value) is None:
        raise ValueError("deploy_port_invalid")
    port = int(value, 10)
    if not 1 <= port <= 65535:
        raise ValueError("deploy_port_invalid")
    return str(port)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("deploy_port_invalid", file=sys.stderr)
        return 64
    try:
        port = normalize_deploy_port(args[0])
    except ValueError:
        print("deploy_port_invalid", file=sys.stderr)
        return 64
    print(port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
