#!/usr/bin/env python3
"""Build a WorkBuddy Token connector from the canonical Skills."""

import argparse
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def build_package(output: Path, skill: str | None = None) -> None:
    entries = {}
    source_root = ROOT / "skills" / skill if skill else ROOT / "skills"
    archive_root = source_root if skill else ROOT
    if not skill:
        adapter = ROOT / "integrations" / "workbuddy"
        entries = {name: adapter / name for name in (
            "connector-meta.json", "mcp.json", "token-schema.json",
        )}
        for source in entries.values():
            json.loads(source.read_text(encoding="utf-8"))
        entries["icon.png"] = ROOT / "skills/transcript-insights/assets/videotranscriberai-logo.png"
    for source in sorted(source_root.rglob("*")):
        if (source.is_file() and "__pycache__" not in source.parts
                and not source.name.startswith(".") and source.suffix != ".pyc"):
            entries[source.relative_to(archive_root).as_posix()] = source
    for source in entries.values():
        if not source.is_file():
            raise FileNotFoundError(f"Missing package input: {source}")
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}; choose a new output path.")
    if output.resolve().is_relative_to((ROOT / "skills").resolve()):
        raise ValueError("Write the archive outside the canonical skills directory.")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, source in sorted(entries.items()):
            archive.write(source, name)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill", choices=sorted(path.name for path in (ROOT / "skills").iterdir() if path.is_dir()))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or ROOT / "dist" / f"{args.skill or 'videotranscriber-workbuddy'}.zip"
    try:
        build_package(output, args.skill)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    print(f"Package written to {output}")


if __name__ == "__main__":
    main()
