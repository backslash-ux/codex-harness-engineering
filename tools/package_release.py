#!/usr/bin/env python3
"""Build a deterministic plugin archive from the canonical public source."""

from __future__ import annotations

import argparse
import json
import stat
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "codex-harness-engineering"
MANIFEST = PLUGIN / ".codex-plugin" / "plugin.json"
LICENSE = ROOT / "LICENSE"
ARCHIVE_ROOT = "codex-harness-engineering"
IGNORED_PARTS = {"__pycache__", ".ruff_cache"}


def release_version() -> str:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return str(data["version"])


def archive_files() -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = []
    for path in sorted(PLUGIN.rglob("*")):
        if not path.is_file() or any(part in IGNORED_PARTS for part in path.parts):
            continue
        relative = path.relative_to(PLUGIN).as_posix()
        files.append((path, f"{ARCHIVE_ROOT}/{relative}"))
    files.append((LICENSE, f"{ARCHIVE_ROOT}/LICENSE"))
    return files


def write_file(archive: zipfile.ZipFile, source: Path, destination: str) -> None:
    info = zipfile.ZipInfo(destination, date_time=(1980, 1, 1, 0, 0, 0))
    mode = stat.S_IMODE(source.stat().st_mode)
    info.external_attr = (stat.S_IFREG | mode) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, source.read_bytes())


def build(output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w") as archive:
        for source, destination in archive_files():
            write_file(archive, source, destination)
    return output


def main() -> int:
    version = release_version()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=(ROOT / "dist" / f"codex-harness-engineering-plugin-v{version}.zip"),
    )
    args = parser.parse_args()
    output = build(args.output.resolve())
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
