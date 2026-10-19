"""Exercise the connector archive users and the WorkBuddy reviewer receive."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts" / "build_workbuddy_connector.py"


class WorkBuddyPackageTests(unittest.TestCase):
    def test_single_skill_upload_archive_has_its_entrypoint_and_references(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "setup.zip"
            result = subprocess.run(
                [sys.executable, str(BUILDER), "--skill", "setup-videotranscriber", "--output", str(output)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(archive.read("SKILL.md"), (ROOT / "skills/setup-videotranscriber/SKILL.md").read_bytes())
                self.assertIn("references/clients.md", archive.namelist())
                self.assertNotIn("connector-meta.json", archive.namelist())

    def test_archive_contains_canonical_skills_and_matching_credential_form(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "connector.zip"
            result = subprocess.run(
                [sys.executable, str(BUILDER), "--output", str(output)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with zipfile.ZipFile(output) as archive:
                for name in ("setup-videotranscriber", "transcribe-media", "transcript-insights"):
                    path = f"skills/{name}/SKILL.md"
                    self.assertEqual(archive.read(path), (ROOT / path).read_bytes())
                self.assertIn("icon.png", archive.namelist())
                self.assertTrue(all(not name.startswith(("/", "../")) for name in archive.namelist()))
                metadata = json.loads(archive.read("connector-meta.json"))
                servers = json.loads(archive.read("mcp.json"))["mcpServers"]
                fields = json.loads(archive.read("token-schema.json"))["fields"]
                self.assertEqual(metadata["auth_mode"], "token")
                self.assertEqual(len(servers), 1)
                server = next(iter(servers.values()))
                self.assertEqual(server["url"], "https://videotranscriber.ai/mcp")
                self.assertEqual(server["headers"]["Authorization"], "Bearer ${" + fields[0]["key"] + "}")
                self.assertEqual(fields[0]["type"], "password")

    def test_existing_archive_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "connector.zip"
            output.write_bytes(b"existing-user-data")
            result = subprocess.run(
                [sys.executable, str(BUILDER), "--output", str(output)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("already exists", result.stderr)
            self.assertEqual(output.read_bytes(), b"existing-user-data")


if __name__ == "__main__":
    unittest.main()
