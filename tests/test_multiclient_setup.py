"""Client formats and production gateway regressions; no real credentials."""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/setup-videotranscriber/scripts/configure_client.py'
KEY = 'vs_test_not_a_real_credential'


class MultiClientTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('multiclient_helper', SCRIPT)
        cls.helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.helper)

    def test_client_transport_formats_and_other_settings_are_preserved(self):
        cases = (
            ('claude-code', 'mcpServers', 'url', 'http'),
            ('workbuddy', 'mcpServers', 'url', 'streamableHttp'),
            ('cursor', 'mcpServers', 'url', None),
            ('windsurf', 'mcpServers', 'serverUrl', None),
            ('gemini-cli', 'mcpServers', 'httpUrl', None),
            ('copilot-cli', 'mcpServers', 'url', 'http'),
            ('vscode', 'servers', 'url', 'http'),
            ('cline', 'mcpServers', 'url', 'streamableHttp'),
            ('roo-code', 'mcpServers', 'url', 'streamable-http'),
        )
        for client, root, url_field, transport in cases:
            with self.subTest(client=client), tempfile.TemporaryDirectory() as folder:
                config = Path(folder) / 'config.json'
                original = {'theme': 'keep', root: {'other': {'command': 'keep-me'}}}
                config.write_text(json.dumps(original))
                result = self.helper.setup_client(client, config, read_key=lambda: KEY, verify=lambda key: None)
                data = json.loads(config.read_text())
                self.assertEqual(data['theme'], 'keep')
                self.assertEqual(data[root]['other'], original[root]['other'])
                entry = data[root]['videotranscriber']
                self.assertEqual(entry[url_field], self.helper.ENDPOINT)
                self.assertEqual(entry['headers']['Authorization'], 'Bearer ' + KEY)
                self.assertEqual(entry.get('type'), transport)
                self.assertFalse(result['client_connection_verified'])
                self.assertTrue(result['reload_required'])
                if client in ('cline', 'roo-code'):
                    self.assertIs(entry['disabled'], False)
                if client == 'copilot-cli':
                    self.assertEqual(set(entry['tools']), self.helper.TOOLS)

    def test_endpoint_alias_is_reused_without_a_duplicate_connection(self):
        raw = json.dumps({'mcpServers': {'video_notes': {
            'serverUrl': self.helper.ENDPOINT, 'headers': {'Authorization': 'Bearer ' + KEY},
            'timeout': 90}}})
        data = json.loads(self.helper.new_config('windsurf', raw, KEY))
        self.assertEqual(list(data['mcpServers']), ['video_notes'])
        self.assertEqual(data['mcpServers']['video_notes']['timeout'], 90)

    def test_jsonc_input_preserves_comments_and_unrelated_text(self):
        raw = '''// User notes: https://example.invalid/a//b
{
  "theme": "keep", // retain this comment
  "servers": {
    "other": {"url": "https://other.invalid/mcp",},
  },
  "inputs": [],
}
'''
        result = self.helper.new_config('vscode', raw, KEY)
        self.assertIn('// retain this comment', result)
        self.assertIn('"other": {"url": "https://other.invalid/mcp",}', result)
        data, entry = self.helper.parse_config('vscode', result)
        self.assertEqual(data['theme'], 'keep')
        self.assertEqual(entry['headers']['Authorization'], 'Bearer ' + KEY)

    def test_jsonc_existing_entry_is_replaced_without_touching_siblings(self):
        raw = '''{"mcpServers": {
  /* keep server notes */ "other": {"command": "keep"},
  "videotranscriber": {"url": "https://videotranscriber.ai/mcp", "headers": {"authorization": "Bearer old"},},
}, "theme": "dark",}'''
        result = self.helper.new_config('cursor', raw, KEY)
        self.assertIn('/* keep server notes */ "other": {"command": "keep"}', result)
        data, entry = self.helper.parse_config('cursor', result)
        self.assertEqual(data['theme'], 'dark')
        self.assertEqual(entry['headers'], {'Authorization': 'Bearer ' + KEY})

    def test_wrong_endpoint_and_conflicting_aliases_do_not_get_overwritten(self):
        for client, entry in (
            ('windsurf', {'serverUrl': 'https://other.invalid/mcp'}),
            ('gemini-cli', {'httpUrl': self.helper.ENDPOINT, 'url': 'https://other.invalid/sse'}),
        ):
            with self.subTest(client=client), self.assertRaises(self.helper.SetupError):
                self.helper.new_config(client, json.dumps({'mcpServers': {'videotranscriber': entry}}), KEY)

    def test_auth_errors_are_distinguished_from_gateway_rejections(self):
        cases = (
            (403, b'{"message":"blocked by Cloudflare"}', 'access_blocked'),
            (403, b'<html>Access denied</html>', 'access_blocked'),
            (401, b'<html>Upstream login required</html>', 'access_blocked'),
            (401, b'{"error":{"code":"invalid_api_key"}}', 'invalid_key'),
            (401, b'{"error":{"code":"api_key_revoked"}}', 'key_revoked'),
            (403, b'{"error":{"code":"api_account_disabled"}}', 'account_disabled'),
            (503, b'{"error":{"code":"authentication_unavailable"}}', 'service_unavailable'),
        )
        for status, body, expected in cases:
            class Transport:
                def open(self, request, timeout):
                    raise HTTPError('https://videotranscriber.ai/mcp', status, KEY, {}, io.BytesIO(body + b' '))
            with self.subTest(status=status, expected=expected), self.assertRaises(self.helper.SetupError) as caught:
                self.helper.verify_key(KEY, opener=Transport())
            self.assertEqual(caught.exception.code, expected)
            self.assertEqual(caught.exception.details['http_status'], status)
            self.assertEqual(caught.exception.details['operation'], 'initialize')
            self.assertNotIn(KEY, str(caught.exception))

    def test_discovery_identifies_itself_to_the_gateway(self):
        class Response(io.BytesIO):
            headers = {}
        class Transport:
            def open(inner, request, timeout):
                agent = request.get_header('User-agent', '')
                self.assertTrue(agent.startswith('VideoTranscriber-Local-Setup/'))
                body = json.loads(request.data)
                if body['method'] == 'initialize':
                    result = {'protocolVersion': '2025-03-26'}
                elif body['method'] == 'tools/list':
                    result = {'tools': [{'name': name} for name in self.helper.TOOLS]}
                else:
                    return Response(b'')
                return Response(json.dumps({'jsonrpc': '2.0', 'id': body['id'], 'result': result}).encode())
        self.helper.verify_key(KEY, opener=Transport())

    def test_default_paths_are_user_scoped(self):
        home = Path('/example-user')
        cases = {
            'codex': '.codex/config.toml', 'claude-code': '.claude.json',
            'workbuddy': '.workbuddy/mcp.json', 'cursor': '.cursor/mcp.json',
            'windsurf': '.codeium/windsurf/mcp_config.json',
            'gemini-cli': '.gemini/settings.json', 'copilot-cli': '.copilot/mcp-config.json',
            'vscode': 'Library/Application Support/Code/User/mcp.json',
        }
        for client, relative in cases.items():
            with self.subTest(client=client):
                self.assertEqual(self.helper.default_config(client, home=home, platform='darwin', environ={}), home / relative)

    def test_extension_path_discovery_requires_a_unique_existing_config(self):
        for client, extension, filename in (
            ('cline', 'saoudrizwan.claude-dev', 'cline_mcp_settings.json'),
            ('roo-code', 'rooveterinaryinc.roo-cline', 'mcp_settings.json'),
        ):
            with self.subTest(client=client), tempfile.TemporaryDirectory() as folder:
                home = Path(folder)
                base = home / 'Library/Application Support'
                path = base / 'Code/User/globalStorage' / extension / 'settings' / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('{}')
                self.assertEqual(self.helper.default_config(client, home=home, platform='darwin', environ={}), path)
                other = base / 'Cursor/User/globalStorage' / extension / 'settings' / filename
                other.parent.mkdir(parents=True, exist_ok=True)
                other.write_text('{}')
                with self.assertRaises(self.helper.SetupError) as caught:
                    self.helper.default_config(client, home=home, platform='darwin', environ={})
                self.assertEqual(caught.exception.code, 'config_selection_required')

    def test_windsurf_uses_existing_relocated_cascade_config(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            actual = home / '.config/devin/mcp_config.json'
            actual.parent.mkdir(parents=True)
            actual.write_text('{}')
            self.assertEqual(self.helper.default_config('windsurf', home=home, platform='darwin', environ={}), actual)
            legacy = home / '.codeium/windsurf/mcp_config.json'
            legacy.parent.mkdir(parents=True)
            legacy.write_text('{}')
            with self.assertRaises(self.helper.SetupError) as caught:
                self.helper.default_config('windsurf', home=home, platform='darwin', environ={})
            self.assertEqual(caught.exception.code, 'config_selection_required')

    def test_editor_profiles_are_not_silently_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            user = home / 'Library/Application Support/Code/User'
            default = user / 'mcp.json'
            profile = user / 'profiles/work/mcp.json'
            profile.parent.mkdir(parents=True)
            profile.write_text('{}')
            default.write_text('{}')
            with self.assertRaises(self.helper.SetupError) as caught:
                self.helper.default_config('vscode', home=home, platform='darwin', environ={})
            self.assertEqual(caught.exception.code, 'config_selection_required')

    def test_active_profile_is_not_inferred_from_an_inactive_mcp_file(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            profiles = home / 'Library/Application Support/Code/User/profiles'
            for name in ('active', 'inactive'):
                (profiles / name).mkdir(parents=True)
                (profiles / name / 'settings.json').write_text('{}')
            (profiles / 'inactive/mcp.json').write_text('{}')
            with self.assertRaises(self.helper.SetupError) as caught:
                self.helper.default_config('vscode', home=home, platform='darwin', environ={})
            self.assertEqual(caught.exception.code, 'config_selection_required')

    def test_portable_named_profile_requires_explicit_active_path(self):
        with tempfile.TemporaryDirectory() as folder:
            portable = Path(folder)
            (portable / 'user-data/User/profiles/work').mkdir(parents=True)
            with self.assertRaises(self.helper.SetupError) as caught:
                self.helper.default_config('vscode', home=portable, platform='linux', environ={'VSCODE_PORTABLE': str(portable)})
            self.assertEqual(caught.exception.code, 'config_selection_required')

    def test_extension_does_not_guess_between_editors_when_one_has_no_mcp_file(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            root = home / 'Library/Application Support'
            for editor in ('Code', 'Cursor'):
                (root / editor / 'User').mkdir(parents=True)
            inactive = root / 'Code/User/globalStorage/saoudrizwan.claude-dev/settings/cline_mcp_settings.json'
            inactive.parent.mkdir(parents=True)
            inactive.write_text('{}')
            with self.assertRaises(self.helper.SetupError) as caught:
                self.helper.default_config('cline', home=home, platform='darwin', environ={})
            self.assertEqual(caught.exception.code, 'config_selection_required')

    def test_windsurf_does_not_guess_between_installed_product_directories(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            (home / '.codeium/windsurf').mkdir(parents=True)
            actual = home / '.config/devin/mcp_config.json'
            actual.parent.mkdir(parents=True)
            actual.write_text('{}')
            with self.assertRaises(self.helper.SetupError) as caught:
                self.helper.default_config('windsurf', home=home, platform='linux', environ={})
            self.assertEqual(caught.exception.code, 'config_selection_required')

    def test_new_insiders_configuration_uses_the_installed_editor(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            user = home / 'Library/Application Support/Code - Insiders/User'
            user.mkdir(parents=True)
            self.assertEqual(self.helper.default_config('vscode', home=home, platform='darwin', environ={}), user / 'mcp.json')

    def test_new_relocated_cascade_configuration_uses_the_installed_product(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            user = home / '.config/devin'
            user.mkdir(parents=True)
            self.assertEqual(self.helper.default_config('windsurf', home=home, platform='linux', environ={}), user / 'mcp_config.json')

    def test_path_resolution_respects_windows_linux_and_custom_roots(self):
        home = Path('/example-user')
        cases = (
            ('vscode', 'win32', {'APPDATA': '/custom-roaming'}, '/custom-roaming/Code/User/mcp.json'),
            ('vscode', 'linux', {'XDG_CONFIG_HOME': '/custom-config'}, '/custom-config/Code/User/mcp.json'),
            ('vscode', 'linux', {'VSCODE_PORTABLE': '/portable'}, '/portable/user-data/User/mcp.json'),
            ('codex', 'linux', {'CODEX_HOME': '/codex-profile'}, '/codex-profile/config.toml'),
            ('copilot-cli', 'linux', {'COPILOT_HOME': '/copilot-profile'}, '/copilot-profile/mcp-config.json'),
            ('cline', 'linux', {'CLINE_MCP_SETTINGS_PATH': '/cline-profile/settings.json'}, '/cline-profile/settings.json'),
        )
        for client, platform, environ, expected in cases:
            with self.subTest(client=client, platform=platform):
                self.assertEqual(self.helper.default_config(client, home=home, platform=platform, environ=environ), Path(expected))

    def test_unknown_client_and_duplicate_json_keys_are_rejected(self):
        for client, raw in (('unknown', '{}'), ('cursor', '{"mcpServers":{}, "mcpServers":{}}')):
            with self.subTest(client=client), self.assertRaises(self.helper.SetupError):
                self.helper.new_config(client, raw, KEY)

    def test_account_and_gateway_failures_preserve_config_without_another_prompt(self):
        for client in self.helper.CLIENTS:
            with self.subTest(client=client), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / 'settings'
                path.write_text(self.helper.new_config(client, '', KEY))
                original = path.read_bytes()
                for error in ('access_blocked', 'account_disabled'):
                    def verify(key):
                        raise self.helper.SetupError(error)
                    with self.assertRaises(self.helper.SetupError) as caught:
                        self.helper.setup_client(client, path, read_key=lambda: self.fail('Unexpected second Key prompt'), verify=verify)
                    self.assertEqual(caught.exception.code, error)
                    self.assertEqual(path.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
