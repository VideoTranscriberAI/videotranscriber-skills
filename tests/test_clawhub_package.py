"""Exercise the exact directory handed to ClawHub and OpenClaw."""

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUILDER = Path("scripts/build_clawhub_bundle.py")
SKILLS = ("setup-videotranscriber", "transcribe-media", "transcript-insights")


def snapshot(root):
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts}


class ClawHubPackageTests(unittest.TestCase):
    def build(self, output, root=ROOT, env=None):
        return subprocess.run([sys.executable, str(root / BUILDER), "--output", str(output)],
                              cwd=root, capture_output=True, text=True, env=env)

    def fixture(self, directory):
        root = Path(directory) / "source"
        shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns(
            ".git", "dist", "__pycache__", ".venv", "implementation-ledger.md"))
        return root

    def test_bundle_connects_the_three_skills_using_only_a_credential_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "bundle"
            result = self.build(output)
            self.assertEqual(result.returncode, 0, result.stderr)
            manifest = json.loads((output / ".codex-plugin/plugin.json").read_text())
            original = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())
            self.assertEqual(manifest["version"], original["version"])
            self.assertEqual(manifest["name"], original["name"])
            self.assertEqual(manifest["license"], "MIT")
            self.assertEqual(manifest["skills"], "./skills/")
            self.assertEqual(manifest["repository"], original["repository"])
            self.assertLessEqual(len(manifest["interface"]["defaultPrompt"]), 3)
            self.assertFalse((output / ".claude-plugin").exists())
            self.assertFalse((output / "openclaw.plugin.json").exists())
            self.assertFalse((output / "package.json").exists())
            servers = json.loads((output / ".mcp.json").read_text())["mcpServers"]
            self.assertEqual(list(servers), ["videotranscriber"])
            self.assertEqual(servers["videotranscriber"]["url"], "https://videotranscriber.ai/mcp")
            self.assertEqual(servers["videotranscriber"]["transport"], "streamable-http")
            self.assertEqual(servers["videotranscriber"]["headers"],
                             {"Authorization": "Bearer ${VS_API_KEY}"})
            self.assertNotIn("oauth", json.dumps(servers).lower())
            for skill in SKILLS:
                source = (ROOT / "skills" / skill / "SKILL.md").read_text()
                packaged = (output / "skills" / skill / "SKILL.md").read_text()
                self.assertEqual(source.split("---", 2)[2], packaged.split("---", 2)[2])
                self.assertIn("openclaw:", packaged.split("---", 2)[1])
                self.assertNotIn("requires:", packaged.split("---", 2)[1])
            self.assertEqual((output / "LICENSE").read_bytes(), (ROOT / "LICENSE").read_bytes())
            self.assertEqual((output / "assets/icon.png").read_bytes(),
                             (ROOT / "skills/transcript-insights/assets/videotranscriberai-logo.png").read_bytes())

    def test_build_never_interpolates_a_credential_from_the_builders_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "bundle"
            canary = "clawhub-test-value-must-not-be-bundled"
            result = self.build(output, env={**os.environ, "VS_API_KEY": canary})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn(canary, result.stdout + result.stderr)
            self.assertTrue(all(canary.encode() not in p.read_bytes()
                                for p in output.rglob("*") if p.is_file()))

    def test_existing_output_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "bundle"
            output.mkdir()
            (output / "user-data").write_text("keep")
            result = self.build(output)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("already exists", result.stderr)
            self.assertEqual(snapshot(output), {"user-data": hashlib.sha256(b"keep").hexdigest()})

    def test_input_tree_is_not_used_as_an_output_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            before = snapshot(root)
            result = self.build(root / "skills" / "release", root)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(snapshot(root), before)

    def test_only_allowlisted_source_files_are_copied_and_source_is_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            (root / "skills/setup-videotranscriber/.env").write_text("PRIVATE=canary")
            (root / "skills/setup-videotranscriber/credentials.json").write_text('{"key":"canary"}')
            (root / "skills/setup-videotranscriber/local-transcript.md").write_text("private transcript")
            before = snapshot(root)
            output = Path(directory) / "bundle"
            result = self.build(output, root)
            self.assertEqual(result.returncode, 0, result.stderr)
            paths = [p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()]
            self.assertFalse(any("credentials" in p or "local-transcript" in p or p.endswith(".env") for p in paths))
            self.assertEqual(snapshot(root), before)

    def test_missing_required_input_fails_before_creating_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            (root / "skills/transcribe-media/references/tool-contract.md").unlink()
            output = Path(directory) / "bundle"
            result = self.build(output, root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Missing package input", result.stderr)
            self.assertFalse(output.exists())

    def test_symlinked_input_cannot_import_a_file_outside_the_package(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            target = root / "skills/transcribe-media/references/tool-contract.md"
            target.unlink()
            outside = Path(directory) / "outside.md"
            outside.write_text("private material")
            target.symlink_to(outside)
            output = Path(directory) / "bundle"
            result = self.build(output, root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symbolic link", result.stderr)
            self.assertFalse(output.exists())

    def test_a_link_outside_the_allowlist_is_rejected_before_output_is_written(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            skill = root / "skills/transcribe-media/SKILL.md"
            skill.write_text(skill.read_text() + "\n[Private](../../private.md)\n")
            (root / "private.md").write_text("not distributable")
            output = Path(directory) / "bundle"
            result = self.build(output, root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Unpackaged local link", result.stderr)
            self.assertFalse(output.exists())

    def test_incorrect_authentication_template_is_rejected_without_copying_its_value(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.fixture(directory)
            path = root / "integrations/clawhub/mcp.json"
            template = json.loads(path.read_text())
            template["mcpServers"]["videotranscriber"]["headers"]["Authorization"] = "Bearer not-a-real-key"
            path.write_text(json.dumps(template))
            output = Path(directory) / "bundle"
            result = self.build(output, root)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("not-a-real-key", result.stdout + result.stderr)
            self.assertFalse(output.exists())

    def test_all_packaged_relative_markdown_links_resolve_in_the_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "bundle"
            result = self.build(output)
            self.assertEqual(result.returncode, 0, result.stderr)
            for file in output.rglob("*.md"):
                for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", file.read_text()):
                    path = target.split("#", 1)[0]
                    if path and not path.startswith(("http:", "https:", "mailto:")):
                        self.assertTrue((file.parent / path).resolve().is_relative_to(output.resolve()))
                        self.assertTrue((file.parent / path).exists(), (file, target))


if __name__ == "__main__":
    unittest.main()
