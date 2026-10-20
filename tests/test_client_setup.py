"""Exercise local credential setup without real credentials or a live API."""

import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import tomllib
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/setup-videotranscriber/scripts/configure_client.py'
KEY = 'vs_test_dummy-not-a-real-key'


class ClientSetupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helper = None
        if SCRIPT.is_file():
            spec = importlib.util.spec_from_file_location('vs_client_setup', SCRIPT)
            cls.helper = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.helper)

    def setUp(self):
        self.assertIsNotNone(self.helper, 'The packaged local configuration helper is missing')
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.config = Path(self.folder.name) / 'config'

    def setup_client(self, client='codex', **kwargs):
        return self.helper.setup_client(client, self.config, read_key=lambda: KEY,
                                        verify=lambda key: None, **kwargs)

    def test_codex_preserves_other_settings_and_removes_stale_auth_sources(self):
        self.config.write_text('''# keep this comment
model = "example"
[mcp_servers.videotranscriber]
url = "https://videotranscriber.ai/mcp"
bearer_token_env_var = "VS_API_KEY"
tool_timeout_sec = 90
[mcp_servers.videotranscriber.env_http_headers]
Authorization = "OLD_KEY"
X-Trace = "TRACE_VARIABLE"
[mcp_servers.other]
url = "https://other.invalid/mcp"
''')
        result = self.setup_client()
        content = self.config.read_text()
        parsed = tomllib.loads(content)
        entry = parsed['mcp_servers']['videotranscriber']
        self.assertEqual(entry['http_headers']['Authorization'], 'Bearer ' + KEY)
        self.assertNotIn('bearer_token_env_var', entry)
        self.assertEqual(entry['env_http_headers'], {'X-Trace': 'TRACE_VARIABLE'})
        self.assertEqual(entry['tool_timeout_sec'], 90)
        self.assertEqual(parsed['mcp_servers']['other']['url'], 'https://other.invalid/mcp')
        self.assertIn('# keep this comment', content)
        self.assertIsNone(result['reload_required'])
        self.assertEqual(result['next_action'], 'discover_client_tools')
        self.assertFalse(result['client_connection_verified'])
        self.assertNotIn(KEY, json.dumps(result))
        if os.name != 'nt':
            self.assertEqual(stat.S_IMODE(self.config.stat().st_mode), 0o600)

    def test_claude_preserves_other_servers_and_user_preferences(self):
        self.config.write_text(json.dumps({'theme': 'dark', 'mcpServers': {
            'other': {'type': 'stdio', 'command': 'example'},
            'videotranscriber': {'type': 'http', 'url': 'https://videotranscriber.ai/mcp',
                                 'headers': {'X-Trace': 'keep'}, 'headersHelper': 'old-command'}}}))
        self.setup_client('claude-code')
        data = json.loads(self.config.read_text())
        self.assertEqual(data['theme'], 'dark')
        self.assertEqual(data['mcpServers']['other'], {'type': 'stdio', 'command': 'example'})
        entry = data['mcpServers']['videotranscriber']
        self.assertEqual(entry['headers'], {'X-Trace': 'keep', 'Authorization': 'Bearer ' + KEY})
        self.assertNotIn('headersHelper', entry)

    def test_wrong_key_does_not_change_existing_configuration(self):
        self.config.write_text('model = "keep"\n')
        def reject(key):
            raise self.helper.SetupError('invalid_key')
        with self.assertRaises(self.helper.SetupError):
            self.helper.setup_client('codex', self.config, read_key=lambda: KEY, verify=reject)
        self.assertEqual(self.config.read_text(), 'model = "keep"\n')

    def test_cancel_leaves_no_configuration_file(self):
        def cancel():
            raise self.helper.SetupError('cancelled')
        with self.assertRaises(self.helper.SetupError):
            self.helper.setup_client('codex', self.config, read_key=cancel, verify=lambda key: None)
        self.assertFalse(self.config.exists())

    def test_existing_valid_key_is_reused_without_asking_again(self):
        self.setup_client()
        before = self.config.read_bytes()
        def unexpected_prompt():
            self.fail('A valid saved credential must not be requested again')
        result = self.helper.setup_client('codex', self.config, read_key=unexpected_prompt,
                                          verify=lambda key: None)
        self.assertFalse(result['configuration_saved'])
        self.assertEqual(self.config.read_bytes(), before)

    @unittest.skipIf(os.name == 'nt', 'POSIX permission regression')
    def test_reused_credential_permissions_are_restricted(self):
        self.setup_client()
        os.chmod(self.config, 0o644)
        self.setup_client()
        self.assertEqual(stat.S_IMODE(self.config.stat().st_mode), 0o600)

    def test_check_accepts_readable_inline_toml_without_rewriting_it(self):
        original = 'mcp_servers = {videotranscriber = {url = "https://videotranscriber.ai/mcp", http_headers = {Authorization = "Bearer ' + KEY + '"}}}\n'
        self.config.write_text(original)
        result = self.setup_client(check=True)
        self.assertEqual(result['status'], 'credential_verified')
        self.assertEqual(self.config.read_text(), original)

    def test_discovery_accepts_sse_without_waiting_for_the_stream_to_close(self):
        class Response(io.BytesIO):
            headers = {'Content-Type': 'text/event-stream'}
            def read(self, *args):
                raise AssertionError('SSE discovery must read events rather than wait for EOF')
        class Transport:
            def open(self, request, timeout):
                body = json.loads(request.data)
                if body['method'] == 'initialize':
                    result = {'protocolVersion': '2025-03-26'}
                elif body['method'] == 'tools/list':
                    result = {'tools': [{'name': name} for name in
                        ('create_transcription', 'get_transcription', 'get_transcription_result')]}
                else:
                    return Response(b'')
                payload = json.dumps({'jsonrpc': '2.0', 'id': body['id'], 'result': result})
                return Response((': heartbeat\n\nevent: message\ndata: ' + payload + '\n\n').encode())
        self.helper.verify_key(KEY, opener=Transport())

    def test_different_endpoint_is_not_overwritten(self):
        original = '[mcp_servers.videotranscriber]\nurl = "https://private.invalid/mcp"\n'
        self.config.write_text(original)
        with self.assertRaises(self.helper.SetupError):
            self.setup_client()
        self.assertEqual(self.config.read_text(), original)

    def test_simultaneous_client_edit_is_preserved(self):
        self.config.write_text('model = "original"\n')
        def verify(key):
            self.config.write_text('model = "concurrent-edit"\n')
        with self.assertRaises(self.helper.SetupError):
            self.helper.setup_client('codex', self.config, read_key=lambda: KEY, verify=verify)
        self.assertEqual(self.config.read_text(), 'model = "concurrent-edit"\n')

    def test_symlink_destination_is_not_followed(self):
        target = Path(self.folder.name) / 'other.toml'
        target.write_text('model = "keep"\n')
        self.config.symlink_to(target)
        with self.assertRaises(self.helper.SetupError):
            self.setup_client()
        self.assertEqual(target.read_text(), 'model = "keep"\n')

    def test_table_like_text_inside_multiline_string_is_preserved(self):
        original = 'note = """\n[mcp_servers.videotranscriber]\nexample only\n"""\n'
        self.config.write_text(original)
        self.setup_client()
        data = tomllib.loads(self.config.read_text())
        self.assertEqual(data['note'], '[mcp_servers.videotranscriber]\nexample only\n')

    def test_existing_environment_credential_is_persisted_without_another_paste(self):
        self.config.write_text('[mcp_servers.videotranscriber]\nurl = "https://videotranscriber.ai/mcp"\nbearer_token_env_var = "VS_API_KEY"\n')
        with patch.dict(os.environ, {'VS_API_KEY': KEY}):
            result = self.setup_client()
        entry = tomllib.loads(self.config.read_text())['mcp_servers']['videotranscriber']
        self.assertNotIn('bearer_token_env_var', entry)
        self.assertEqual(entry['http_headers']['Authorization'], 'Bearer ' + KEY)
        self.assertTrue(result['configuration_saved'])

    def test_disabled_connection_is_enabled_using_its_saved_key(self):
        self.config.write_text('[mcp_servers.videotranscriber]\nurl = "https://videotranscriber.ai/mcp"\nenabled = false\nhttp_headers = {Authorization = "Bearer ' + KEY + '"}\n')
        self.setup_client()
        self.assertTrue(tomllib.loads(self.config.read_text())['mcp_servers']['videotranscriber']['enabled'])

    def test_check_never_rewrites_configuration(self):
        self.config.write_text('[mcp_servers.videotranscriber]\nurl = "https://videotranscriber.ai/mcp"\nbearer_token_env_var = "VS_API_KEY"\n')
        before = self.config.read_bytes()
        with patch.dict(os.environ, {'VS_API_KEY': KEY}):
            self.setup_client(check=True)
        self.assertEqual(before, self.config.read_bytes())

    def test_ui_key_never_appears_in_command_arguments_or_status_output(self):
        result = __import__('subprocess').CompletedProcess([], 0, stdout=KEY + '\n', stderr='')
        output = io.StringIO()
        with patch.object(self.helper.sys, 'platform', 'darwin'), patch.object(self.helper.subprocess, 'run', return_value=result) as process, patch('sys.stdout', output):
            value = self.helper.read_key('auto', 'zh')
        self.assertEqual(value, KEY)
        self.assertNotIn(KEY, json.dumps(process.call_args.args))
        self.assertNotIn(KEY, output.getvalue())

    def test_ui_failure_reports_an_unavailable_input_instead_of_cancellation(self):
        result = __import__('subprocess').CompletedProcess([], 1, stdout='', stderr='Application interaction is not allowed (-1743)')
        with patch.object(self.helper.sys, 'platform', 'darwin'), patch.object(self.helper.subprocess, 'run', return_value=result), patch('sys.stdout', io.StringIO()), self.assertRaises(self.helper.SetupError) as caught:
            self.helper.read_key('auto')
        self.assertEqual(caught.exception.code, 'input_unavailable')

    def test_existing_connection_with_another_name_is_updated_without_duplicates(self):
        for client, original in (
            ('codex', '[mcp_servers.video_notes]\nurl = "https://videotranscriber.ai/mcp"\nbearer_token_env_var = "VS_API_KEY"\n'),
            ('claude-code', '{"mcpServers":{"video_notes":{"type":"http","url":"https://videotranscriber.ai/mcp"}}}'),
        ):
            with self.subTest(client=client):
                self.config.write_text(original)
                self.setup_client(client)
                data = tomllib.loads(self.config.read_text()) if client == 'codex' else json.loads(self.config.read_text())
                self.assertEqual(set(data['mcp_servers' if client == 'codex' else 'mcpServers']), {'video_notes'})

    def test_terminal_input_refuses_a_noninteractive_agent_session(self):
        with patch.object(self.helper.sys.stdin, 'isatty', return_value=False), patch('sys.stdout', io.StringIO()), self.assertRaises(self.helper.SetupError) as caught:
            self.helper.read_key('terminal')
        self.assertEqual(caught.exception.code, 'input_unavailable')

    def test_permission_failure_preserves_original_and_removes_temporary_file(self):
        self.config.write_text('model = "keep"\n')
        with patch.object(self.helper, 'private_permissions', side_effect=self.helper.SetupError('permission_failed')), self.assertRaises(self.helper.SetupError):
            self.setup_client()
        self.assertEqual(self.config.read_text(), 'model = "keep"\n')
        self.assertEqual([path.name for path in Path(self.folder.name).iterdir()], ['config'])

    def test_malformed_configuration_is_not_replaced(self):
        self.config.write_text('[broken')
        with self.assertRaises(self.helper.SetupError):
            self.setup_client()
        self.assertEqual(self.config.read_text(), '[broken')

    def test_verification_uses_discovery_and_never_calls_a_paid_tool(self):
        requests = []
        class Response(io.BytesIO):
            headers = {}
        class Transport:
            def open(self, request, timeout):
                body = json.loads(request.data)
                requests.append((body['method'], request.get_header('Authorization')))
                if body['method'] == 'initialize':
                    payload = {'protocolVersion': '2025-03-26', 'capabilities': {'tools': {}},
                               'serverInfo': {'name': 'Video Transcriber AI', 'version': '1.0'}}
                elif body['method'] == 'tools/list':
                    payload = {'tools': [{'name': name} for name in
                        ('create_transcription', 'get_transcription', 'get_transcription_result')]}
                else:
                    return Response(b'')
                return Response(json.dumps({'jsonrpc': '2.0', 'id': body['id'], 'result': payload}).encode())
        self.helper.verify_key(KEY, opener=Transport())
        self.assertEqual([method for method, _ in requests],
                         ['initialize', 'notifications/initialized', 'tools/list'])
        self.assertTrue(all(header == 'Bearer ' + KEY for _, header in requests))

    def test_network_and_auth_errors_do_not_echo_server_content(self):
        for error in (HTTPError('https://videotranscriber.ai/mcp', 401, KEY, {}, io.BytesIO(KEY.encode())),
                      URLError(KEY)):
            class Transport:
                def open(self, request, timeout):
                    raise error
            with self.subTest(error=type(error).__name__), self.assertRaises(self.helper.SetupError) as caught:
                self.helper.verify_key(KEY, opener=Transport())
            self.assertNotIn(KEY, str(caught.exception))

    def test_empty_or_unexpected_discovery_response_is_rejected(self):
        for body in (b'', b'not-json', b'{"jsonrpc":"2.0","id":1,"result":{}}'):
            class Transport:
                def open(self, request, timeout):
                    response = io.BytesIO(body)
                    response.headers = {}
                    return response
            with self.subTest(body=body), self.assertRaises(self.helper.SetupError):
                self.helper.verify_key(KEY, opener=Transport())


if __name__ == '__main__':
    unittest.main()
