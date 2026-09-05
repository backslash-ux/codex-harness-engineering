#!/usr/bin/env python3
"""Check or install the managed user-level repository alignment contract."""

from __future__ import annotations

import argparse
import os
import stat
import tempfile
from pathlib import Path

START = "<!-- harness-engineering:global-contract:start -->"
END = "<!-- harness-engineering:global-contract:end -->"


def contract_text() -> str:
    asset = (
        Path(__file__).resolve().parent.parent / "assets" / "global-contract.md.tmpl"
    )
    text = asset.read_text(encoding="utf-8").strip()
    if text.count(START) != 1 or text.count(END) != 1:
        raise ValueError("global contract asset must contain exactly one managed block")
    return text


def inspect(current: str, expected: str) -> str:
    starts = current.count(START)
    ends = current.count(END)
    if starts != ends or starts > 1:
        return "malformed"
    if starts == 0:
        return "absent"
    begin = current.index(START)
    if current.index(END) < begin:
        return "malformed"
    finish = current.index(END, begin) + len(END)
    managed = current[begin:finish].strip()
    return "installed" if managed == expected else "divergent"


def install(target: Path, expected: str) -> str:
    current = target.read_text(encoding="utf-8") if target.exists() else ""
    status = inspect(current, expected)
    if status == "installed":
        return "unchanged"
    if status in {"divergent", "malformed"}:
        raise ValueError(f"refusing to replace {status} managed content in {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    prefix = current.rstrip()
    updated = (prefix + "\n\n" if prefix else "") + expected + "\n"
    mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else 0o600
    descriptor, name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            os.fchmod(stream.fileno(), mode)
            stream.write(updated)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return "installed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--install", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    target = args.target.expanduser().resolve()
    if target.exists() and not target.is_file():
        parser.error(f"target is not a file: {target}")
    try:
        expected = contract_text()
    except (OSError, ValueError) as error:
        parser.error(str(error))
    current = target.read_text(encoding="utf-8") if target.exists() else ""
    if args.check:
        print(f"Global contract: {inspect(current, expected)}")
        print(f"Target: {target}")
        return 0
    if not args.confirm:
        parser.error("--install requires --confirm")
    try:
        result = install(target, expected)
    except (OSError, ValueError) as error:
        print(error)
        return 2
    print(f"Global contract: {result}")
    print(f"Target: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
