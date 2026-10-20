"""Offline transport and same-session MCP continuation regressions."""
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/setup-videotranscriber/scripts'
KEY = 'vs_test_continuation_dummy_credential'
TASK = 'req_' + 'a' * 32


def load(name, filename):
    path = SCRIPTS / filename
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Response(io.BytesIO):
    def __init__(self, body, headers=None, short=False):
        super().__init__(body)
        self.headers = headers or {'Content-Type': 'application/json'}
        self.status = 200
        self.short = short

    def read(self, size=-1):
        return super().read(min(size, 23) if self.short and size > 0 else size)


class Transport:
    def __init__(self, results=()):
        self.results = iter(results)
        self.calls = []

    def open(self, request, timeout):
        body = json.loads(request.data)
        self.calls.append(body)
        method = body['method']
        if method == 'notifications/initialized':
            return Response(b'')
        if method == 'initialize':
            result = {'protocolVersion': '2025-03-26'}
        elif method == 'tools/list':
            result = {'tools': [{'name': name} for name in
                ('create_transcription', 'get_transcription', 'get_transcription_result')]}
        else:
            result = next(self.results)
            if isinstance(result, Exception):
                raise result
        return Response(json.dumps({'jsonrpc': '2.0', 'id': body['id'], 'result': result}).encode())


def fake_process(run):
    class Process:
        def __init__(self, argv, **kwargs):
            self.returncode = None
            self.terminated = False
            owner = self
            class Input(io.BytesIO):
                def close(inner):
                    if inner.closed:
                        return
                    value = inner.getvalue()
                    super().close()
                    result = run(argv, input=value, stdout=kwargs['stdout'])
                    owner.returncode = result.returncode
            self.stdin = Input()

        def poll(self):
            return self.returncode

        def terminate(self):
            self.terminated = True
            self.returncode = 0

        def kill(self):
            self.terminate()

        def wait(self, timeout):
            if self.returncode is None:
                raise subprocess.TimeoutExpired('test curl', timeout)
            return self.returncode
    return Process


class ResponseReadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helper = load('read_helper', 'configure_client.py')

    def test_complete_json_is_collected_across_short_reads(self):
        payload = {'jsonrpc': '2.0', 'id': 1, 'result': {'tools': ['tool'] * 100}}
        response = Response(json.dumps(payload).encode(), short=True)
        self.assertEqual(self.helper.response_payload(response, 1), payload)

    def test_incomplete_content_length_is_not_accepted_as_success(self):
        class IncompleteTransport(Transport):
            def open(inner, request, timeout):
                response = super().open(request, timeout)
                if json.loads(request.data)['method'] != 'notifications/initialized':
                    response.headers['Content-Length'] = str(len(response.getvalue()) + 100)
                return response
        with self.assertRaises(self.helper.SetupError) as caught:
            self.helper.verify_key(KEY, opener=IncompleteTransport())
        self.assertEqual(caught.exception.code, 'network_error')
        self.assertNotIn(KEY, str(caught.exception))

    def test_oversized_response_is_reported_without_repeating_discovery(self):
        transport = Transport()
        with self.assertRaises(self.helper.SetupError) as caught:
            self.helper.verify_with_retry(KEY, lambda key: self.helper.mcp_connection(key, opener=transport, max_bytes=10))
        self.assertEqual(caught.exception.code, 'response_too_large')
        self.assertEqual(len(transport.calls), 1)


class CurlTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load('transport_helper', 'mcp_transport.py')

    def setUp(self):
        self.assertIsNotNone(self.module, 'The packaged bounded HTTP transport is missing')

    def test_curl_credentials_are_only_on_stdin_and_response_is_read(self):
        from urllib.request import Request
        seen = []
        def run(argv, **kwargs):
            seen.append((argv, kwargs['input']))
            kwargs['stdout'].write(b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 2\r\n\r\n{}')
            return subprocess.CompletedProcess(argv, 0)
        with patch.object(self.module.subprocess, 'Popen', side_effect=fake_process(run)):
            response = self.module.CurlOpener('/usr/bin/curl').open(
                Request('https://videotranscriber.ai/mcp', data=b'{}',
                    headers={'Authorization': 'Bearer ' + KEY}), timeout=10)
        self.assertEqual(response.read(), b'{}')
        self.assertEqual(response.status, 200)
        argv, config = seen[0]
        self.assertNotIn(KEY, ' '.join(argv))
        self.assertIn(KEY, config.decode())
        self.assertEqual(argv[1], '-q')
        self.assertIn('no-buffer\n', config.decode())
        self.assertNotIn('insecure', config.decode())
        self.assertNotIn('location =', config.decode())

    def test_partial_curl_transfer_is_rejected_without_raw_stderr(self):
        from urllib.request import Request
        def run(argv, **kwargs):
            kwargs['stdout'].write(b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{"broken":')
            return subprocess.CompletedProcess(argv, 18, stderr=KEY)
        with patch.object(self.module.subprocess, 'Popen', side_effect=fake_process(run)), self.assertRaises(URLError) as caught:
            self.module.CurlOpener('/usr/bin/curl').open(Request('https://videotranscriber.ai/mcp', data=b'{}'), timeout=10)
        self.assertNotIn(KEY, str(caught.exception))

    def test_curl_does_not_follow_redirects(self):
        from urllib.request import Request
        def run(argv, **kwargs):
            kwargs['stdout'].write(b'HTTP/1.1 302 Found\r\nLocation: https://other.invalid/\r\n\r\n')
            return subprocess.CompletedProcess(argv, 0)
        with patch.object(self.module.subprocess, 'Popen', side_effect=fake_process(run)), self.assertRaises(HTTPError) as caught:
            self.module.CurlOpener('/usr/bin/curl').open(Request('https://videotranscriber.ai/mcp', data=b'{}'), timeout=10)
        self.assertEqual(caught.exception.code, 302)
        caught.exception.close()

    def test_other_endpoints_are_rejected_before_curl_runs(self):
        from urllib.request import Request
        with patch.object(self.module.subprocess, 'Popen') as run, self.assertRaises(ValueError):
            self.module.CurlOpener('/usr/bin/curl').open(Request('https://other.invalid/mcp', data=b'{}'), timeout=10)
        run.assert_not_called()

    def test_auto_mode_uses_urllib_when_curl_is_missing(self):
        fallback = object()
        with patch.object(self.module.shutil, 'which', return_value=None):
            self.assertIs(self.module.default_opener('auto', lambda: fallback), fallback)

    def test_generated_config_is_accepted_by_real_curl_without_network(self):
        executable = self.module.shutil.which('curl')
        if not executable:
            self.skipTest('curl is optional')
        from urllib.request import Request
        captured = []
        real_run = subprocess.run
        def run(argv, **kwargs):
            captured.append(kwargs['input'])
            kwargs['stdout'].write(b'HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n{}')
            return subprocess.CompletedProcess(argv, 0)
        with patch.object(self.module.subprocess, 'Popen', side_effect=fake_process(run)):
            self.module.CurlOpener(executable).open(Request('https://videotranscriber.ai/mcp',
                data=b'{"method":"tools/list"}', headers={'Authorization': 'Bearer ' + KEY}), timeout=10)
        result = real_run([executable, '-q', '--config', '-', '--version'], input=captured[0],
                          capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertIn(b'curl ', result.stdout)

    def test_complete_matching_sse_returns_while_connection_remains_open(self):
        from urllib.request import Request
        def run(argv, **kwargs):
            kwargs['stdout'].write(b'HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\n\r\n'
                b'data: {"jsonrpc":"2.0","id":7,"result":{"ready":true}}\n\n')
            return subprocess.CompletedProcess(argv, None)
        created = []
        factory = fake_process(run)
        def spawn(*args, **kwargs):
            process = factory(*args, **kwargs)
            created.append(process)
            return process
        with (patch.object(self.module.subprocess, 'Popen', side_effect=spawn),
              patch.object(self.module.time, 'sleep', side_effect=AssertionError('A complete event must return immediately'))):
            response = self.module.CurlOpener('/usr/bin/curl').open(Request('https://videotranscriber.ai/mcp',
                data=b'{"jsonrpc":"2.0","id":7,"method":"tools/list"}'), timeout=10)
        self.assertIn(b'"ready":true',response.read())
        self.assertTrue(created[0].terminated)

    def test_sse_without_matching_event_times_out_and_reaps_process(self):
        from urllib.request import Request
        def run(argv, **kwargs):
            kwargs['stdout'].write(b'HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\n\r\n'
                b'data: {"jsonrpc":"2.0","id":99,"result":{}}\n\n')
            return subprocess.CompletedProcess(argv, None)
        created = []
        factory = fake_process(run)
        def spawn(*args, **kwargs):
            process = factory(*args, **kwargs)
            created.append(process)
            return process
        with (patch.object(self.module.subprocess, 'Popen', side_effect=spawn),
              patch.object(self.module.time, 'monotonic', side_effect=[0,100]),
              self.assertRaises(URLError)):
            self.module.CurlOpener('/usr/bin/curl').open(Request('https://videotranscriber.ai/mcp',
                data=b'{"jsonrpc":"2.0","id":7,"method":"tools/list"}'), timeout=10)
        self.assertTrue(created[0].terminated)


class ContinuationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = load('mcp_runner', 'call_mcp.py')

    def setUp(self):
        self.assertIsNotNone(self.runner, 'The packaged same-session MCP caller is missing')
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.config = Path(self.folder.name) / 'config.toml'
        self.config.write_text('[mcp_servers.videotranscriber]\nurl = "https://videotranscriber.ai/mcp"\nhttp_headers = {Authorization = "Bearer ' + KEY + '"}\n')

    def run_tool(self, tool, arguments, transport, **kwargs):
        return self.runner.run_tool('codex', self.config, tool, arguments, opener=transport, **kwargs)

    def test_saved_credential_runs_without_a_dialog_or_config_change(self):
        original = self.config.read_bytes()
        transport = Transport([{'structuredContent': {'id': TASK, 'status': 'processing'}, 'isError': False}])
        result = self.run_tool('create_transcription', {'source_url': 'https://example.com/lesson.mp4', 'idempotency_key': 'one-task'}, transport)
        self.assertEqual(result['result']['id'], TASK)
        self.assertEqual(self.config.read_bytes(), original)
        self.assertNotIn(KEY, json.dumps(result))

    def test_saved_credentials_work_for_every_supported_client_profile(self):
        for client in self.runner.helper.CLIENTS:
            with self.subTest(client=client):
                path = Path(self.folder.name) / (client + '.config')
                path.write_text(self.runner.helper.new_config(client, '', KEY))
                original = path.read_bytes()
                transport = Transport([{'structuredContent': {'id': TASK, 'status': 'processing'}}])
                result = self.runner.run_tool(client, path, 'get_transcription', {'request_id': TASK}, opener=transport)
                self.assertEqual(result['result']['id'], TASK)
                self.assertEqual(path.read_bytes(), original)

    def test_uncertain_creation_retries_with_identical_arguments_and_key(self):
        transport = Transport([URLError('connection lost'), {'structuredContent': {'id': TASK, 'status': 'processing'}}])
        arguments = {'source_url': 'https://example.com/lesson.mp4', 'idempotency_key': 'keep-this-key'}
        updates = []
        with patch.object(self.runner.helper.time, 'sleep'):
            self.run_tool('create_transcription', arguments, transport, report=updates.append)
        calls = [item for item in transport.calls if item['method'] == 'tools/call']
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0], calls[1])
        self.assertEqual(calls[0]['params']['arguments'], arguments)
        self.assertNotIn(KEY, json.dumps(updates))

    def test_quota_error_is_returned_without_retry_or_recreation(self):
        transport = Transport([{'isError': True, '_meta': {'http_status': 402},
            'structuredContent': {'error': {'code': 'insufficient_quota', 'retryable': False}}}])
        result = self.run_tool('create_transcription', {'source_url': 'https://example.com/a.mp4', 'idempotency_key': 'one'}, transport)
        self.assertEqual(result['status'], 'tool_error')
        self.assertEqual(result['result']['error']['code'], 'insufficient_quota')
        self.assertEqual(sum(item['method'] == 'tools/call' for item in transport.calls), 1)

    def test_result_larger_than_discovery_limit_is_retrieved_and_links_are_private(self):
        transcript = 'a' * 300000
        signed = 'https://download.invalid/result?signature=private'
        transport = Transport([{'structuredContent': {'id': TASK, 'transcript': {'text': transcript},
            'downloads': {'srt': {'url': signed}}}}])
        result = self.run_tool('get_transcription_result', {'request_id': TASK}, transport)
        self.assertEqual(result['result']['transcript']['text'], transcript)
        self.assertNotIn(signed, json.dumps(result))

    def test_explicit_download_request_can_include_result_links(self):
        signed = 'https://download.invalid/result?signature=private'
        transport = Transport([{'structuredContent': {'downloads': {'srt': {'url': signed}}}}])
        result = self.run_tool('get_transcription_result', {'request_id': TASK}, transport, include_download_links=True)
        self.assertEqual(result['result']['downloads']['srt']['url'], signed)

    def test_wrong_endpoint_is_rejected_without_network_access(self):
        self.config.write_text(self.config.read_text().replace('videotranscriber.ai/mcp', 'other.invalid/mcp'))
        transport = Transport()
        with self.assertRaises(self.runner.helper.SetupError):
            self.run_tool('get_transcription', {'request_id': TASK}, transport)
        self.assertEqual(transport.calls, [])

    def test_missing_credential_never_prompts(self):
        self.config.write_text('model = "keep"\n')
        with self.assertRaises(self.runner.helper.SetupError) as caught:
            self.run_tool('get_transcription', {'request_id': TASK}, Transport())
        self.assertEqual(caught.exception.code, 'key_missing')

    def test_creation_requires_explicit_retained_idempotency_key(self):
        transport = Transport()
        with self.assertRaises(self.runner.helper.SetupError) as caught:
            self.run_tool('create_transcription', {'source_url': 'https://example.com/a.mp4'}, transport)
        self.assertEqual(caught.exception.code, 'invalid_arguments')
        self.assertEqual(transport.calls, [])

    def test_credentials_are_rejected_as_tool_arguments(self):
        transport = Transport()
        with self.assertRaises(self.runner.helper.SetupError):
            self.run_tool('get_transcription', {'request_id': TASK, 'api_key': KEY}, transport)
        self.assertEqual(transport.calls, [])

    def test_text_content_json_is_supported_without_structured_content(self):
        transport = Transport([{'content': [{'type': 'text', 'text': json.dumps({'id': TASK, 'status': 'succeeded'})}]}])
        result = self.run_tool('get_transcription', {'request_id': TASK}, transport)
        self.assertEqual(result['result']['status'], 'succeeded')

    def test_successful_status_with_null_error_is_not_a_tool_error(self):
        transport = Transport([{'structuredContent': {'id': TASK, 'status': 'succeeded', 'error': None}}])
        result = self.run_tool('get_transcription', {'request_id': TASK}, transport)
        self.assertEqual(result['status'], 'completed')

    def test_text_validation_error_is_reported_once_without_another_submission(self):
        transport = Transport([{'isError': True, 'content': [{'type': 'text',
            'text': 'Invalid language; diagnostic must not echo ' + KEY}]}])
        result = self.run_tool('get_transcription', {'request_id': TASK}, transport)
        self.assertEqual(result['status'], 'tool_error')
        self.assertEqual(sum(item['method'] == 'tools/call' for item in transport.calls), 1)
        self.assertNotIn(KEY, json.dumps(result))

    def test_rpc_validation_error_is_not_retried(self):
        class InvalidArguments(Transport):
            def open(inner, request, timeout):
                body = json.loads(request.data)
                if body['method'] == 'tools/call':
                    inner.calls.append(body)
                    return Response(json.dumps({'jsonrpc': '2.0', 'id': body['id'],
                        'error': {'code': -32602, 'message': KEY}}).encode())
                return super().open(request, timeout)
        transport = InvalidArguments()
        with self.assertRaises(self.runner.helper.SetupError) as caught:
            self.run_tool('get_transcription', {'request_id': TASK}, transport)
        self.assertEqual(caught.exception.code, 'rpc_error')
        self.assertEqual(sum(item['method'] == 'tools/call' for item in transport.calls), 1)
        self.assertNotIn(KEY, str(caught.exception))

    def test_setup_curl_retry_keeps_one_input_until_verification_succeeds(self):
        helper = self.runner.helper
        self.config.write_text('model = "keep"\n')
        inputs = []
        processes = []
        def run(argv, **kwargs):
            config = kwargs['input'].decode()
            data = next(line.split('=', 1)[1].strip() for line in config.splitlines() if line.startswith('data-binary ='))
            request = json.loads(json.loads(data))
            processes.append(request)
            if len(processes) == 1:
                raw = b'{'
            elif request['method'] == 'initialize':
                raw = json.dumps({'jsonrpc':'2.0','id':1,'result':{'protocolVersion':'2025-03-26'}}).encode()
            elif request['method'] == 'tools/list':
                raw = json.dumps({'jsonrpc':'2.0','id':2,'result':{'tools':[{'name':name} for name in helper.TOOLS]}}).encode()
            else:
                raw = b''
            kwargs['stdout'].write(b'HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: ' + str(len(raw)).encode() + b'\r\n\r\n' + raw)
            return subprocess.CompletedProcess(argv, 0)
        def read():
            inputs.append(True)
            return KEY
        with (patch.object(helper._transport.shutil, 'which', return_value='/usr/bin/curl'),
              patch.object(helper._transport.subprocess, 'Popen', side_effect=fake_process(run)),
              patch.object(helper.time, 'sleep')):
            result = helper.setup_client('codex', self.config, read_key=read)
        self.assertEqual(len(inputs), 1)
        self.assertEqual(result['status'], 'credential_verified')
        self.assertEqual(len(processes), 4)

    def test_result_file_is_complete_private_and_preserves_existing_data(self):
        path = Path(self.folder.name) / 'result.json'
        result = {'status': 'completed', 'result': {'transcript': {'text': 'a' * 300000}}}
        self.runner.write_result(path, result)
        self.assertEqual(json.loads(path.read_text()), result)
        if os.name != 'nt':
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        original = path.read_bytes()
        with self.assertRaises(self.runner.helper.SetupError) as caught:
            self.runner.write_result(path, {'replace': True})
        self.assertEqual(caught.exception.code, 'output_exists')
        self.assertEqual(path.read_bytes(), original)

    def test_result_cli_emits_file_summary_instead_of_a_long_transcript(self):
        path = Path(self.folder.name) / 'result.json'
        result = {'status': 'completed', 'tool': 'get_transcription_result', 'http_status': 200,
                  'result': {'transcript': {'text': 'long transcript ' * 10000}}}
        output = io.StringIO()
        argv = ['call_mcp.py','--client','codex','--tool','get_transcription_result',
                '--arguments',json.dumps({'request_id':TASK}),'--output',str(path)]
        with patch.object(self.runner.sys,'argv',argv), patch.object(self.runner,'run_tool',return_value=result), patch('sys.stdout',output):
            code = self.runner.main()
        self.assertEqual(code, 0)
        self.assertNotIn('long transcript',output.getvalue())
        self.assertEqual(json.loads(output.getvalue())['result_file'],str(path))
        self.assertEqual(json.loads(path.read_text()),result)

    def test_existing_result_file_stops_cli_before_network_access(self):
        path = Path(self.folder.name) / 'result.json'
        path.write_text('keep this file')
        argv = ['call_mcp.py','--client','codex','--tool','get_transcription_result',
                '--arguments',json.dumps({'request_id':TASK}),'--output',str(path)]
        output = io.StringIO()
        with patch.object(self.runner.sys,'argv',argv), patch.object(self.runner,'run_tool') as run, patch('sys.stdout',output):
            code = self.runner.main()
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(output.getvalue())['code'],'output_exists')
        self.assertEqual(path.read_text(),'keep this file')
        run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
