#!/usr/bin/env python3
"""Validate repository-level Agent Skill and plugin invariants."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"{path.relative_to(ROOT)}: {exc}")


def load_skill_frontmatter(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        fail(f"{path.relative_to(ROOT)} must start with YAML frontmatter")
    try:
        _, raw, body = text.split("---", 2)
        metadata = yaml.safe_load(raw)
    except (ValueError, yaml.YAMLError) as exc:
        fail(f"{path.relative_to(ROOT)} has invalid frontmatter: {exc}")
    if not isinstance(metadata, dict):
        fail(f"{path.relative_to(ROOT)} frontmatter must be a mapping")
    return metadata, body


def validate_markdown_links(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for target in MARKDOWN_LINK_PATTERN.findall(text):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        local_target = target.split("#", 1)[0].strip()
        if local_target.startswith("<") and local_target.endswith(">"):
            local_target = local_target[1:-1]
        if local_target and not (path.parent / local_target).resolve().exists():
            fail(f"{path.relative_to(ROOT)} contains a broken local link: {target}")


def discover_skills() -> list[Path]:
    if not SKILLS_DIR.is_dir():
        fail("Missing skills directory")
    skills = sorted(
        path
        for path in SKILLS_DIR.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )
    if not skills:
        fail("The repository must contain at least one Skill")
    return skills


def validate_skill(skill_dir: Path) -> None:
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        fail(f"{skill_dir.relative_to(ROOT)} is missing SKILL.md")

    metadata, body = load_skill_frontmatter(skill_file)
    if set(metadata) != {"name", "description"}:
        fail(
            f"{skill_file.relative_to(ROOT)} frontmatter must contain only "
            "name and description"
        )
    if (
        metadata["name"] != skill_dir.name
        or not NAME_PATTERN.fullmatch(str(metadata["name"]))
    ):
        fail(
            f"{skill_file.relative_to(ROOT)} name and directory must match "
            "lowercase kebab-case"
        )
    if not str(metadata["description"]).strip():
        fail(f"{skill_file.relative_to(ROOT)} description must not be empty")
    if "[TODO:" in body:
        fail(f"{skill_file.relative_to(ROOT)} contains an unfinished TODO")

    openai_yaml_path = skill_dir / "agents" / "openai.yaml"
    if not openai_yaml_path.is_file():
        fail(f"{skill_dir.relative_to(ROOT)} is missing agents/openai.yaml")
    openai_yaml = yaml.safe_load(
        openai_yaml_path.read_text(encoding="utf-8")
    )
    if not isinstance(openai_yaml, dict):
        fail(f"{openai_yaml_path.relative_to(ROOT)} must contain a mapping")
    default_prompt = openai_yaml.get("interface", {}).get("default_prompt", "")
    if f"${skill_dir.name}" not in default_prompt:
        fail(
            f"{openai_yaml_path.relative_to(ROOT)} default_prompt must explicitly "
            f"name ${skill_dir.name}"
        )
    if openai_yaml.get("policy", {}).get("allow_implicit_invocation") is not True:
        fail(
            f"{openai_yaml_path.relative_to(ROOT)} must allow implicit invocation"
        )

    example_dir = ROOT / "examples" / skill_dir.name
    if not example_dir.is_dir() or not any(example_dir.iterdir()):
        fail(f"Missing non-empty examples/{skill_dir.name} directory")
    test_cases = ROOT / "tests" / skill_dir.name / "cases.md"
    if not test_cases.is_file():
        fail(f"Missing tests/{skill_dir.name}/cases.md")

    for markdown_file in skill_dir.rglob("*.md"):
        validate_markdown_links(markdown_file)


def validate_plugin_manifests() -> None:
    codex = load_json(ROOT / ".codex-plugin" / "plugin.json")
    claude = load_json(ROOT / ".claude-plugin" / "plugin.json")
    codex_marketplace = load_json(ROOT / ".agents" / "plugins" / "marketplace.json")
    claude_marketplace = load_json(ROOT / ".claude-plugin" / "marketplace.json")

    expected_name = "videotranscriber-skills"
    expected_version = codex.get("version", "")
    if not re.fullmatch(r"\d+\.\d+\.\d+", expected_version):
        fail("Plugin version must use semantic versioning")
    for label, manifest in (("Codex", codex), ("Claude", claude)):
        if manifest.get("name") != expected_name:
            fail(f"{label} plugin name does not match {expected_name}")
        if manifest.get("version") != expected_version:
            fail(f"{label} plugin version does not match {expected_version}")

    for label, marketplace in (
        ("Codex", codex_marketplace),
        ("Claude", claude_marketplace),
    ):
        names = [entry.get("name") for entry in marketplace.get("plugins", [])]
        if expected_name not in names:
            fail(f"{label} marketplace does not expose {expected_name}")
        for entry in marketplace.get("plugins", []):
            if entry.get("name") == expected_name and "version" in entry and entry["version"] != expected_version:
                fail(f"{label} marketplace version does not match the plugin")


def validate_connection_packages() -> None:
    endpoint = "https://videotranscriber.ai/mcp"
    claude = load_json(ROOT / ".claude-plugin/plugin.json")
    credential = claude.get("userConfig", {}).get("api_key", {})
    server = claude.get("mcpServers", {}).get("videotranscriber", {})
    if server.get("url") != endpoint or server.get("headers", {}).get("Authorization") != "Bearer ${user_config.api_key}":
        fail("Claude MCP must reference the plugin credential")
    if credential.get("sensitive") is not True or credential.get("required") is not False or "default" in credential:
        fail("Claude credential must be sensitive and optional, with no bundled default")

    adapter = ROOT / "integrations/workbuddy"
    metadata = load_json(adapter / "connector-meta.json")
    server = load_json(adapter / "mcp.json")["mcpServers"]["videotranscriber"]
    fields = load_json(adapter / "token-schema.json").get("fields", [])
    if len(fields) != 1 or fields[0].get("type") != "password" or not fields[0].get("required") or "defaultValue" in fields[0]:
        fail("WorkBuddy must collect one required password field without a credential default")
    expected_header = "Bearer ${" + fields[0]["key"] + "}"
    if server.get("url") != endpoint or server.get("headers", {}).get("Authorization") != expected_header:
        fail("WorkBuddy token form and MCP credential placeholder do not match")
    if metadata.get("auth_mode") != "token" or metadata.get("minWorkbuddyVersion") != "4.24.0":
        fail("WorkBuddy must declare Token mode and its bilingual-example version floor")
    if metadata.get("version") != load_json(ROOT / ".codex-plugin/plugin.json")["version"]:
        fail("WorkBuddy package version does not match the plugin")


def validate_transcript_insights() -> None:
    skill_dir = SKILLS_DIR / "transcript-insights"
    if not skill_dir.is_dir():
        return

    required_examples = {
        "fictional-transcript.md",
        "fictional-transcript.json",
        "fictional-subtitles.srt",
        "fictional-subtitles.vtt",
        "requested-output.md",
        "expected-output.md",
        "official-video-subtitles.srt",
        "official-video-request.md",
        "official-video-expected-output.md",
    }
    example_dir = ROOT / "examples" / "transcript-insights"
    missing = required_examples - {path.name for path in example_dir.iterdir()}
    if missing:
        fail(f"Missing examples: {', '.join(sorted(missing))}")

    json_fixture = load_json(example_dir / "fictional-transcript.json")
    segments = json_fixture.get("segments")
    if not isinstance(segments, list) or not segments:
        fail("Generic JSON fixture must contain a non-empty segments array")
    for index, segment in enumerate(segments, start=1):
        if not isinstance(segment, dict) or not str(segment.get("text", "")).strip():
            fail(f"JSON fixture segment {index} must contain text")
        if "start" not in segment or "end" not in segment:
            fail(f"JSON fixture segment {index} must contain start and end")

    official_srt = (example_dir / "official-video-subtitles.srt").read_text(
        encoding="utf-8"
    )
    srt_blocks = re.split(r"\n\n+", official_srt.strip())
    if len(srt_blocks) != 4:
        fail("Official SRT Demo must contain four normalized cues")
    timestamp_pattern = re.compile(
        r"^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$"
    )
    for expected_index, block in enumerate(srt_blocks, start=1):
        lines = block.splitlines()
        if len(lines) < 3 or lines[0] != str(expected_index):
            fail(f"Official SRT cue {expected_index} is malformed")
        if not timestamp_pattern.fullmatch(lines[1]):
            fail(f"Official SRT cue {expected_index} has an invalid timestamp")

    required_outputs = {
        "Executive Summary",
        "Key Insights",
        "Action Items",
        "Open Questions",
        "Translation",
        "Chapters",
        "Key Decisions",
        "Learning Notes",
        "Mind Map",
    }
    output_reference = (
        skill_dir / "references" / "output-types.md"
    ).read_text(encoding="utf-8")
    missing_outputs = required_outputs - {
        output for output in required_outputs if f"## {output}" in output_reference
    }
    if missing_outputs:
        fail(f"Missing output contracts: {', '.join(sorted(missing_outputs))}")


def validate_repository_markdown() -> None:
    for readme_name in ("README.md", "README_zh.md"):
        validate_markdown_links(ROOT / readme_name)
    for path in (
        ROOT / "CONTRIBUTING.md",
        ROOT / "ROADMAP.md",
        ROOT / "RELEASE_NOTES.md",
        ROOT / "docs" / "ARCHITECTURE.md",
    ):
        if not path.is_file():
            fail(f"Missing {path.relative_to(ROOT)}")
        validate_markdown_links(path)

    for path in (ROOT / "docs").rglob("*.md"):
        validate_markdown_links(path)


def main() -> None:
    skills = discover_skills()
    for skill_dir in skills:
        validate_skill(skill_dir)
    validate_plugin_manifests()
    validate_connection_packages()
    validate_transcript_insights()
    validate_repository_markdown()

    print(f"Repository validation passed for {len(skills)} Skill(s).")


if __name__ == "__main__":
    main()
