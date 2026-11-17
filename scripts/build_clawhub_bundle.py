#!/usr/bin/env python3
"""Build an allowlisted Codex-format bundle for ClawHub without publishing it."""

import argparse
import copy
import json
from pathlib import Path, PurePosixPath
import posixpath
import re


ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://videotranscriber.ai/mcp"
SKILL_FILES = {
    "setup-videotranscriber": (
        "SKILL.md", "agents/openai.yaml", "scripts/configure_client.py",
        "scripts/call_mcp.py", "scripts/mcp_transport.py", "references/clients.md",
        "references/local-setup.md", "references/first-run.md", "references/openclaw.md",
    ),
    "transcribe-media": ("SKILL.md", "agents/openai.yaml", "references/tool-contract.md"),
    "transcript-insights": (
        "SKILL.md", "agents/openai.yaml", "assets/videotranscriberai-logo.png",
        "references/json-input.md", "references/output-types.md", "references/quality-rules.md",
    ),
}
EXPECTED_MCP = {"mcpServers": {"videotranscriber": {
    "url": ENDPOINT, "transport": "streamable-http",
    "headers": {"Authorization": "Bearer ${VS_API_KEY}"},
}}}


def read_input(root: Path, relative: str) -> bytes:
    path = root / relative
    for candidate in (path, *path.parents):
        if candidate == root:
            break
        if candidate.is_symlink():
            raise ValueError(f"Package input is a symbolic link: {relative}")
    if not path.is_file():
        raise ValueError(f"Missing package input: {relative}")
    return path.read_bytes()


def read_json(root: Path, relative: str) -> dict:
    try:
        value = json.loads(read_input(root, relative))
    except (ValueError, UnicodeError) as error:
        # Preserve our safe path-only input errors; never echo JSON values.
        if isinstance(error, ValueError) and str(error).startswith(("Missing package input:", "Package input is a symbolic link:")):
            raise
        raise ValueError(f"Invalid JSON package input: {relative}") from None
    if not isinstance(value, dict):
        raise ValueError(f"Package input must be a JSON object: {relative}")
    return value


def add_openclaw_metadata(content: bytes, skill: str) -> bytes:
    text = content.decode("utf-8")
    if not text.startswith("---\n") or len(text.split("---", 2)) != 3:
        raise ValueError(f"Invalid Skill frontmatter: {skill}")
    _, frontmatter, body = text.split("---", 2)
    if re.search(r"^metadata:", frontmatter, re.MULTILINE):
        raise ValueError(f"Canonical Skill already declares metadata: {skill}")
    metadata = ("metadata:\n  openclaw:\n"
                "    homepage: https://videotranscriber.ai/\n")
    if skill != "transcript-insights":
        metadata += ("    primaryEnv: VS_API_KEY\n    envVars:\n"
                     "      - name: VS_API_KEY\n        required: false\n"
                     "        description: Gateway credential for the optional transcription connection.\n")
    return ("---" + frontmatter.rstrip() + "\n" + metadata + "---" + body).encode("utf-8")


def validate_entries(entries: dict[str, bytes]) -> None:
    for relative, content in entries.items():
        if not relative.endswith(".md"):
            continue
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", content.decode("utf-8")):
            target = target.split("#", 1)[0].strip().strip("<>")
            if not target or target.startswith(("https://", "http://", "mailto:")):
                continue
            normalized = posixpath.normpath(posixpath.join(str(PurePosixPath(relative).parent), target))
            if normalized not in entries:
                raise ValueError(f"Unpackaged local link in {relative}: {target}")


def package_entries(root: Path = ROOT) -> dict[str, bytes]:
    """Resolve and validate every output byte before creating a directory."""
    root = root.resolve()
    manifest = read_json(root, ".codex-plugin/plugin.json")
    template = read_json(root, "integrations/clawhub/plugin.json")
    mcp = read_json(root, "integrations/clawhub/mcp.json")
    if mcp != EXPECTED_MCP:
        raise ValueError("ClawHub MCP must use the official endpoint, Streamable HTTP and the VS_API_KEY reference")
    if set(template) != {"interface"} or not isinstance(template["interface"], dict):
        raise ValueError("ClawHub plugin template must contain only interface overrides")
    manifest = copy.deepcopy(manifest)
    manifest["interface"].update(template["interface"])
    prompts = manifest["interface"].get("defaultPrompt", [])
    if (not isinstance(prompts, list) or not 1 <= len(prompts) <= 3
            or any(not isinstance(p, str) or not p.strip() or len(p) > 128 for p in prompts)):
        raise ValueError("ClawHub requires one to three recommended prompts of at most 128 characters")
    if (manifest.get("name") != "videotranscriber-skills" or manifest.get("skills") != "./skills/"
            or manifest.get("license") != "MIT"
            or not re.fullmatch(r"\d+\.\d+\.\d+", str(manifest.get("version", "")))):
        raise ValueError("Canonical plugin identity, Skill root, MIT license or version is invalid")
    entries = {
        ".codex-plugin/plugin.json": (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode(),
        ".mcp.json": (json.dumps(mcp, indent=2) + "\n").encode(),
        "README.md": read_input(root, "integrations/clawhub/README.md"),
        "LICENSE": read_input(root, "LICENSE"),
        "assets/icon.png": read_input(root, "skills/transcript-insights/assets/videotranscriberai-logo.png"),
    }
    if len(entries["assets/icon.png"]) > 512 * 1024 or not entries["assets/icon.png"].startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("ClawHub icon must be a PNG no larger than 512 KiB")
    for skill, files in SKILL_FILES.items():
        for name in files:
            relative = f"skills/{skill}/{name}"
            content = read_input(root, relative)
            entries[relative] = add_openclaw_metadata(content, skill) if name == "SKILL.md" else content
    for field in ("composerIcon", "logo"):
        if posixpath.normpath(manifest["interface"].get(field, "")) not in entries:
            raise ValueError(f"Unpackaged plugin {field}")
    validate_entries(entries)
    return entries


def build_package(output: Path, root: Path = ROOT) -> None:
    root = root.resolve()
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise FileExistsError("Output already exists; choose a new output path")
    resolved = output.resolve()
    if resolved == root or (resolved.is_relative_to(root) and not resolved.is_relative_to(root / "dist")):
        raise ValueError("Write the bundle outside the source tree or under dist/")
    entries = package_entries(root)
    output.mkdir(parents=True, exist_ok=False)
    for relative, content in entries.items():
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(content)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/clawhub/videotranscriber-skills")
    parser.add_argument("--check", action="store_true", help="Validate package inputs without creating output")
    args = parser.parse_args()
    try:
        if args.check:
            entries = package_entries()
            print(f"ClawHub package inputs passed ({len(entries)} files).")
        else:
            build_package(args.output)
            print(f"ClawHub bundle written to {args.output}")
    except (OSError, ValueError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
