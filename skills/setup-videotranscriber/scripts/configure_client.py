#!/usr/bin/env python3
"""Configure the active local AI client's MCP connection using private Key input.

Requires Python 3.11+. No third-party packages. This command never creates a
transcription. Credentials are stored in the client's plaintext user config.
"""

import argparse
import csv
from email.utils import parsedate_to_datetime
import getpass
from http.client import IncompleteRead
import importlib.util
import io
import json
from math import ceil
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import warnings
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

try:
    import tomllib
except ModuleNotFoundError:
    print('{"status":"error","code":"python_3_11_required"}')
    raise SystemExit(1)


_transport_spec = importlib.util.spec_from_file_location(
    'videotranscriber_transport', Path(__file__).with_name('mcp_transport.py'))
_transport = importlib.util.module_from_spec(_transport_spec)
_transport_spec.loader.exec_module(_transport)

ENDPOINT = 'https://videotranscriber.ai/mcp'
USER_AGENT = 'VideoTranscriber-Local-Setup/0.4.2'
TOOLS = {'create_transcription', 'get_transcription', 'get_transcription_result'}
CLIENTS = {
    'codex': ('mcp_servers', 'url', None),
    'claude-code': ('mcpServers', 'url', 'http'),
    'workbuddy': ('mcpServers', 'url', 'streamableHttp'),
    'cursor': ('mcpServers', 'url', None),
    'windsurf': ('mcpServers', 'serverUrl', None),
    'gemini-cli': ('mcpServers', 'httpUrl', None),
    'copilot-cli': ('mcpServers', 'url', 'http'),
    'vscode': ('servers', 'url', 'http'),
    'cline': ('mcpServers', 'url', 'streamableHttp'),
    'roo-code': ('mcpServers', 'url', 'streamable-http'),
}
URL_FIELDS = ('url', 'serverUrl', 'httpUrl')
ERRORS = {
    'cancelled': 'Cancelled; the existing configuration was kept.',
    'invalid_key': 'The Key was rejected. Create or copy an active API Key and try again.',
    'key_revoked': 'The API Key has been revoked. Copy an active Key from the API console.',
    'account_disabled': 'The API account is disabled. Check the API account status or contact support.',
    'access_blocked': 'The endpoint or gateway denied access. Check network and service access policies before retrying.',
    'invalid_input': 'The Key is empty or contains unsupported characters. Copy the Key again.',
    'network_error': 'Connection failed or timed out; the existing configuration was kept.',
    'service_unavailable': 'The MCP service is unavailable; retry later.',
    'unexpected_response': 'The service did not return the expected MCP discovery response.',
    'redirect_rejected': 'The service redirected the request; no credential was forwarded.',
    'config_invalid': 'The client configuration could not be parsed; it was not replaced.',
    'config_format': 'This configuration layout needs manual review; it was not replaced.',
    'config_conflict': 'This server name points to another endpoint. Select the intended connection first.',
    'ambiguous_connection': 'Multiple Video Transcriber connections exist. Select the intended connection first.',
    'config_changed': 'The client edited its configuration during setup; retry without changing it.',
    'config_symlink': 'The configuration is a symbolic link; choose its intended user config explicitly.',
    'input_unavailable': 'No private input window is available. Run --input terminal in your own terminal.',
    'key_missing': 'No saved credential was found. Run setup to enter the Key locally.',
    'custom_config': 'A custom Claude configuration directory is in use; supply its user config with --config.',
    'config_selection_required': 'Locate the active user MCP configuration in this client, then supply its path with --config.',
    'unsupported_client': 'This client is not supported by this helper. Use its native MCP credential settings.',
    'permission_failed': 'Private file permissions could not be set; no new configuration was saved.',
    'permission_required': 'Allow the helper network and user-config access before opening private input again.',
    'invalid_arguments': 'Use the supported tool arguments and retain the original idempotency_key.',
    'rpc_error': 'The MCP service rejected this operation; inspect the safe RPC code.',
    'output_exists': 'Choose a new result file; the existing file was preserved.',
    'response_too_large': 'The response exceeds the local size limit; use native tools or a smaller result.',
    'io_error': 'The local configuration could not be saved; check filesystem permissions.',
}


class SetupError(Exception):
    def __init__(self, code, **details):
        self.code = code
        self.details = details
        super().__init__(ERRORS[code])


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SetupError('redirect_rejected')


def clean_key(value):
    value = value.strip()
    if not value or len(value) > 4096 or any(ord(char) < 33 or ord(char) > 126 for char in value) or '${' in value:
        raise SetupError('invalid_input')
    return value


def response_payload(response, request_id, max_bytes=262144):
    if 'text/event-stream' not in response.headers.get('Content-Type', '').lower():
        raw = _transport.read_complete(response, max_bytes)
        if not raw:
            raise SetupError('unexpected_response')
        return json.loads(raw)
    # A valid SSE connection can remain open. Stop after this request's event.
    total = 0
    data = []
    deadline = time.monotonic() + 10
    while total < max_bytes and time.monotonic() < deadline:
        line = response.readline(max_bytes + 1 - total)
        if not line:
            break
        total += len(line)
        if total > max_bytes:
            raise _transport.ResponseTooLarge()
        line = line.decode('utf-8').rstrip('\r\n')
        if line.startswith('data:'):
            data.append(line[5:].lstrip(' '))
        elif not line and data:
            payload = json.loads('\n'.join(data))
            data = []
            if isinstance(payload, dict) and payload.get('id') == request_id:
                return payload
    raise SetupError('unexpected_response')


def mcp_connection(key, opener=None, transport='auto', max_bytes=262144, timeout=10):
    """Initialize the official MCP endpoint; return an authenticated RPC function."""
    key = clean_key(key)
    transport = opener or _transport.default_opener(transport, lambda: build_opener(NoRedirect()))
    headers = {'Authorization': 'Bearer ' + key, 'Accept': 'application/json, text/event-stream',
               'Content-Type': 'application/json', 'User-Agent': USER_AGENT}

    def request(method, request_id=None, params=None):
        body = {'jsonrpc': '2.0', 'method': method}
        if request_id is not None:
            body['id'] = request_id
        if params is not None:
            body['params'] = params
        req = Request(ENDPOINT, data=json.dumps(body).encode(), headers=headers, method='POST')
        details = {'operation': method}
        try:
            with transport.open(req, timeout=timeout) as response:
                status = getattr(response, 'status', None)
                if isinstance(status, int):
                    details['http_status'] = status
                content_type = response.headers.get('Content-Type', '').split(';', 1)[0].strip().lower()
                details['content_type'] = content_type if content_type in (
                    'application/json', 'text/event-stream', 'text/html') else 'other'
                if response.headers.get('Mcp-Session-Id'):
                    session = response.headers['Mcp-Session-Id']
                    if not session or any(ord(char) < 33 or ord(char) > 126 for char in session):
                        raise SetupError('unexpected_response', failure_stage='session_header')
                    headers['Mcp-Session-Id'] = session
                if request_id is None:
                    return None
                payload = response_payload(response, request_id, max_bytes)
            if (not isinstance(payload, dict) or payload.get('id') != request_id
                    or not isinstance(payload.get('result'), dict) or 'error' in payload):
                error = payload.get('error') if isinstance(payload, dict) else None
                if isinstance(error, dict) and isinstance(error.get('code'), int):
                    details['rpc_error_code'] = error['code']
                    if method == 'tools/call':
                        raise SetupError('rpc_error', **details)
                raise SetupError('unexpected_response', failure_stage='rpc_envelope')
            return payload['result']
        except HTTPError as exc:
            # A gateway rejection is not proof that the API rejected the Key.
            status = exc.code
            if 300 <= status < 400:
                exc.close()
                raise SetupError('redirect_rejected', operation=method, http_status=status) from None
            api_code = None
            try:
                payload = json.loads(exc.read(8193))
                error = payload.get('error') if isinstance(payload, dict) else None
                if isinstance(error, dict) and isinstance(error.get('code'), str):
                    api_code = error['code']
            except (ValueError, OSError, UnicodeError):
                pass
            finally:
                exc.close()
            code = {
                (401, 'invalid_api_key'): 'invalid_key',
                (401, 'api_key_revoked'): 'key_revoked',
                (403, 'api_account_disabled'): 'account_disabled',
            }.get((status, api_code), 'access_blocked' if status in (401, 403) else 'service_unavailable')
            info = {'http_status': status, 'operation': method}
            retry_after = exc.headers.get('Retry-After') if exc.headers else None
            if retry_after is not None:
                try:
                    if not isinstance(retry_after, str) or len(retry_after) > 128:
                        raise ValueError
                    retry_after = retry_after.strip()
                    if retry_after.isascii() and retry_after.isdigit() and len(retry_after) <= 8:
                        delay = int(retry_after)
                    else:
                        retry_at = parsedate_to_datetime(retry_after)
                        if retry_at.tzinfo is None:
                            raise ValueError
                        delay = max(0, ceil(retry_at.timestamp() - time.time()))
                    info['retry_after_seconds'] = delay
                except (ValueError, TypeError, OverflowError):
                    info['retry_after_unavailable'] = True
            raise SetupError(code, **info) from None
        except SetupError as exc:
            raise SetupError(exc.code, **{**details, **exc.details}) from None
        except _transport.ResponseTooLarge:
            raise SetupError('response_too_large', **details, max_bytes=max_bytes) from None
        except (URLError, TimeoutError, OSError, IncompleteRead) as exc:
            code = 'permission_required' if isinstance(exc, PermissionError) or isinstance(
                getattr(exc, 'reason', None), PermissionError) else 'network_error'
            curl_code = getattr(exc, 'curl_exit_code', None)
            if isinstance(curl_code, int):
                details['curl_exit_code'] = curl_code
            raise SetupError(code, **details, error_type=type(exc).__name__) from None
        except (ValueError, TypeError, UnicodeError) as exc:
            raise SetupError('unexpected_response', **details,
                             failure_stage='response_decode', error_type=type(exc).__name__) from None

    result = request('initialize', 1, {'protocolVersion': '2025-03-26',
        'capabilities': {}, 'clientInfo': {'name': 'videotranscriber-local-setup', 'version': '1.0'}})
    protocol = result.get('protocolVersion')
    if not isinstance(protocol, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', protocol):
        raise SetupError('unexpected_response', operation='initialize', failure_stage='protocol_version')
    headers['MCP-Protocol-Version'] = protocol
    request('notifications/initialized')
    result = request('tools/list', 2)
    tools = result.get('tools')
    if not isinstance(tools, list) or not TOOLS.issubset({item.get('name') for item in tools
            if isinstance(item, dict) and isinstance(item.get('name'), str)}):
        raise SetupError('unexpected_response', operation='tools/list', failure_stage='tool_list')
    return request


def verify_key(key, opener=None, transport='auto'):
    """Authenticated MCP discovery only; never create a transcription."""
    mcp_connection(key, opener=opener, transport=transport)


def read_key(source='auto', language='en'):
    if source == 'env':
        return clean_key(os.environ.get('VS_API_KEY', ''))
    zh = language == 'zh'
    notice = ('请粘贴 API Key。将以明文保存在客户端本机用户配置中，并限制文件权限。转写使用独立 API 额度。'
              if zh else 'Paste your API Key. It will be saved in the client local plaintext user config with private file permissions. Transcription uses separate API Quota.')
    print(json.dumps({'status': 'awaiting_key', 'input': source, 'storage': 'local_plaintext_user_config',
                      'message': 'Enter the Key in the local input, never in chat.'}), flush=True)
    if source == 'terminal':
        if not sys.stdin.isatty():
            raise SetupError('input_unavailable')
        print(notice, flush=True)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', getpass.GetPassWarning)
                return clean_key(getpass.getpass(('Video Transcriber API Key（输入隐藏）: ' if zh else 'Video Transcriber API Key (hidden): ')))
        except (getpass.GetPassWarning, EOFError):
            raise SetupError('input_unavailable') from None
    if sys.platform == 'darwin':
        # Only fixed display text enters argv; the Key returns over a private pipe.
        message = json.dumps(notice, ensure_ascii=False)
        cancel = json.dumps('取消' if zh else 'Cancel', ensure_ascii=False)
        connect = json.dumps('连接' if zh else 'Connect', ensure_ascii=False)
        script = ('set answer to display dialog ' + message + ' with title "Video Transcriber" '
                  'default answer "" with hidden answer buttons {' + cancel + ', ' + connect + '} '
                  'default button ' + connect + ' cancel button ' + cancel + ' giving up after 300\n'
                  'if gave up of answer then error number -128\nreturn text returned of answer')
        command = ['osascript', '-e', script]
    elif sys.platform == 'win32':
        script = r'''
Add-Type -AssemblyName System.Windows.Forms
$form = New-Object Windows.Forms.Form
$form.Text = 'Video Transcriber'; $form.Width = 520; $form.Height = 230
$form.StartPosition = 'CenterScreen'; $form.TopMost = $true
$label = New-Object Windows.Forms.Label
$label.Text = '__NOTICE__'; $label.SetBounds(20,15,460,65)
$box = New-Object Windows.Forms.TextBox
$box.UseSystemPasswordChar = $true; $box.SetBounds(20,90,460,25)
$ok = New-Object Windows.Forms.Button
$ok.Text = '__CONNECT__'; $ok.SetBounds(285,135,90,30); $ok.DialogResult = 'OK'
$cancel = New-Object Windows.Forms.Button
$cancel.Text = '__CANCEL__'; $cancel.SetBounds(390,135,90,30); $cancel.DialogResult = 'Cancel'
$form.Controls.AddRange(@($label,$box,$ok,$cancel)); $form.AcceptButton = $ok; $form.CancelButton = $cancel
$timer = New-Object Windows.Forms.Timer; $timer.Interval = 300000
$timer.Add_Tick({$form.Close()}); $timer.Start()
if ($form.ShowDialog() -ne 'OK') {exit 2}
[Console]::Write($box.Text)
'''.replace('__NOTICE__', notice.replace("'", "''")).replace('__CONNECT__', '连接' if zh else 'Connect').replace('__CANCEL__', '取消' if zh else 'Cancel')
        command = ['powershell.exe', '-NoProfile', '-STA', '-Command', script]
    elif shutil.which('zenity') and (os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY')):
        command = ['zenity', '--password', '--title=Video Transcriber', '--text=' + notice, '--timeout=300']
    else:
        raise SetupError('input_unavailable')
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=310)
    except subprocess.TimeoutExpired:
        raise SetupError('cancelled') from None
    except OSError:
        raise SetupError('input_unavailable') from None
    if result.returncode:
        cancelled = ('-128' in result.stderr if sys.platform == 'darwin' else
                     result.returncode == 2 if sys.platform == 'win32' else result.returncode in (1, 5))
        if cancelled:
            raise SetupError('cancelled')
        raise SetupError('input_unavailable')
    return clean_key(result.stdout)


def client_profile(client):
    if client not in CLIENTS:
        raise SetupError('unsupported_client')
    return CLIENTS[client]


def endpoint(entry):
    values = [entry[field].rstrip('/') for field in URL_FIELDS
              if isinstance(entry.get(field), str)]
    if len(set(values)) > 1:
        raise SetupError('config_conflict')
    return values[0] if values else ''


def connection_name(client, data):
    servers = data.get(client_profile(client)[0], {})
    if not isinstance(servers, dict):
        raise SetupError('config_invalid')
    matches = [name for name, entry in servers.items() if isinstance(entry, dict)
               and any(isinstance(entry.get(field), str) and entry[field].rstrip('/') == ENDPOINT
                       for field in URL_FIELDS)]
    if len(matches) > 1:
        raise SetupError('ambiguous_connection')
    if 'videotranscriber' in servers:
        return 'videotranscriber'
    return matches[0] if matches else 'videotranscriber'


def json_tokens(raw):
    """Tokenize JSONC without changing positions, including URL-like string contents."""
    pattern = re.compile(r'\s+|//[^\r\n]*|/\*[\s\S]*?\*/|"(?:[^"\\\r\n]|\\.)*"|[{}\[\],:]|[^\s{}\[\],:"/]+')
    result = []
    index = 0
    while index < len(raw):
        match = pattern.match(raw, index)
        if not match:
            raise ValueError()
        text = match.group()
        if not (text.isspace() or text.startswith('//') or text.startswith('/*')):
            result.append((text, match.start(), match.end()))
        index = match.end()
    return result


def json_data(raw):
    tokens = json_tokens(raw or '{}')
    normalized = ' '.join(text for index, (text, _, _) in enumerate(tokens)
                          if not (text == ',' and index + 1 < len(tokens) and tokens[index + 1][0] in ('}', ']')))
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError()
            result[key] = value
        return result
    return json.loads(normalized, object_pairs_hook=unique_object)


def parse_config(client, raw):
    try:
        root = client_profile(client)[0]
        data = tomllib.loads(raw) if client == 'codex' else json_data(raw)
        if not isinstance(data, dict):
            raise ValueError()
        servers = data.get(root, {})
        name = connection_name(client, data)
        if not isinstance(servers.get(name, {}), dict):
            raise ValueError()
        entry = servers.get(name, {})
        if entry and endpoint(entry) != ENDPOINT:
            raise SetupError('config_conflict')
        return data, entry
    except (ValueError, TypeError, AttributeError):
        raise SetupError('config_invalid') from None


def json_text(raw, root, name, entry):
    """Replace/insert only the chosen server, preserving other JSONC text."""
    raw = raw if raw.strip() else '{}\n'
    tokens = json_tokens(raw)
    def value_end(start):
        if tokens[start][0] not in ('{', '['):
            return start + 1
        depth = 0
        for index in range(start, len(tokens)):
            if tokens[index][0] in ('{', '['):
                depth += 1
            elif tokens[index][0] in ('}', ']'):
                depth -= 1
                if depth == 0:
                    return index + 1
        raise SetupError('config_invalid')
    def members(start):
        result = {}
        index = start + 1
        while tokens[index][0] != '}':
            key = json.loads(tokens[index][0])
            end = value_end(index + 2)
            result[key] = (index + 2, end)
            index = end + (tokens[end][0] == ',')
        return result
    def insert(start, key, value):
        closing = value_end(start) - 1
        comma = ',' if members(start) and tokens[closing - 1][0] != ',' else ''
        position = tokens[closing][1]
        addition = comma + '\n' + json.dumps(key) + ': ' + json.dumps(value, indent=2, ensure_ascii=False) + '\n'
        return raw[:position] + addition + raw[position:]
    top = members(0)
    if root not in top:
        return insert(0, root, {name: entry})
    server_start = top[root][0]
    servers = members(server_start)
    if name not in servers:
        return insert(server_start, name, entry)
    start, end = servers[name]
    return raw[:tokens[start][1]] + json.dumps(entry, indent=2, ensure_ascii=False) + raw[tokens[end - 1][2]:]


def toml_value(value):
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        return str(value).lower()
    if isinstance(value, list):
        return '[' + ', '.join(toml_value(item) for item in value) + ']'
    if isinstance(value, dict):
        return '{' + ', '.join(toml_value(key) + ' = ' + toml_value(item) for key, item in value.items()) + '}'
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    raise SetupError('config_format')


def codex_text(raw, entry, name):
    """Replace only explicit tables for this server; validate the complete result."""
    lines = raw.splitlines(keepends=True)
    tables = []
    for index, line in enumerate(lines):
        if not re.match(r'^\s*\[.+\]\s*(?:#.*)?$', line):
            continue
        try:
            tomllib.loads(''.join(lines[:index]))  # Skip lookalike headers inside multiline values.
            sample = tomllib.loads(line + '\n__vs_table_marker__ = true\n')
        except ValueError:
            continue
        path = []
        while isinstance(sample, (dict, list)):
            if isinstance(sample, list):
                sample = sample[-1]
            elif '__vs_table_marker__' in sample:
                break
            else:
                component, sample = next(iter(sample.items()))
                path.append(component)
        tables.append((index, tuple(path)))
    remove = set()
    target = ('mcp_servers', name)
    for position, (start, path) in enumerate(tables):
        if path[:2] == target:
            end = tables[position + 1][0] if position + 1 < len(tables) else len(lines)
            remove.update(range(start, end))
    if parse_config('codex', raw)[1] and not remove:
        raise SetupError('config_format')
    preserved = ''.join(line for index, line in enumerate(lines) if index not in remove)
    block = '[mcp_servers.' + toml_value(name) + ']\n' + ''.join(
        toml_value(key) + ' = ' + toml_value(value) + '\n' for key, value in entry.items())
    return preserved.rstrip() + '\n\n' + block


def new_config(client, raw, key):
    data, existing = parse_config(client, raw)
    root, url_field, transport = client_profile(client)
    name = connection_name(client, data)
    entry = dict(existing)
    header_field = 'http_headers' if client == 'codex' else 'headers'
    headers = entry.get(header_field, {})
    if not isinstance(headers, dict):
        raise SetupError('config_invalid')
    headers = {name: value for name, value in headers.items() if name.lower() != 'authorization'}
    headers['Authorization'] = 'Bearer ' + key
    for field in URL_FIELDS:
        entry.pop(field, None)
    entry.update({url_field: ENDPOINT, header_field: headers})
    if client == 'codex':
        entry.pop('bearer_token_env_var', None)
        entry.pop('http_headers_helper', None)
        for field in ('env_http_headers',):
            values = entry.get(field, {})
            if not isinstance(values, dict):
                raise SetupError('config_invalid')
            if values:
                entry[field] = {name: value for name, value in values.items() if name.lower() != 'authorization'}
        entry['enabled'] = True
        result = codex_text(raw, entry, name)
        expected = dict(data)
        expected['mcp_servers'] = {**data.get('mcp_servers', {}), name: entry}
        if tomllib.loads(result) != expected:
            raise SetupError('config_format')
        return result
    for field in ('headersHelper', 'http_headers_helper', 'auth', 'oauth', 'authProviderType',
                  'command', 'args', 'env', 'envFile'):
        entry.pop(field, None)
    if transport:
        entry['type'] = transport
    else:
        entry.pop('type', None)
    if client in ('cline', 'roo-code'):
        entry['disabled'] = False
    if client == 'copilot-cli':
        entry.setdefault('tools', sorted(TOOLS))
    data[root] = {**data.get(root, {}), name: entry}
    result = json_text(raw, root, name, entry)
    if json_data(result) != data:
        raise SetupError('config_format')
    return result


def private_permissions(path):
    if os.name != 'nt':
        os.chmod(path, 0o600)
        return
    try:
        user = subprocess.run(['whoami', '/user', '/fo', 'csv', '/nh'],
                              capture_output=True, text=True, check=True, timeout=10)
        sid = next(csv.reader(io.StringIO(user.stdout)))[1]
        if not re.fullmatch(r'S-\d(?:-\d+)+', sid):
            raise ValueError()
        subprocess.run(['icacls', str(path), '/inheritance:r', '/grant:r', '*' + sid + ':F'],
                       capture_output=True, check=True, timeout=10)
    except (OSError, ValueError, IndexError, StopIteration, subprocess.SubprocessError):
        raise SetupError('permission_failed') from None


def save_config(path, raw, content):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.videotranscriber-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
            private_permissions(Path(temporary))
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        if path.is_symlink():
            raise SetupError('config_symlink')
        current = path.read_text(encoding='utf-8') if path.exists() else ''
        if current != raw:
            raise SetupError('config_changed')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def saved_key(client, entry):
    headers = entry.get('http_headers' if client == 'codex' else 'headers', {})
    if isinstance(headers, dict):
        for name, value in headers.items():
            if name.lower() == 'authorization' and isinstance(value, str) and value.startswith('Bearer '):
                if '${' not in value:
                    return value[7:]
    if client == 'codex' and isinstance(entry.get('bearer_token_env_var'), str):
        return os.environ.get(entry['bearer_token_env_var'])
    return None


def prepare_config_write(path):
    """Check local write permissions before collecting a credential; store no Key."""
    try:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix='.videotranscriber-access-', dir=path.parent)
        try:
            os.close(descriptor)
            private_permissions(Path(temporary))
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    except PermissionError:
        raise SetupError('permission_required', operation='config_preflight') from None
    except OSError:
        raise SetupError('io_error') from None


def verify_with_retry(key, verify, report=None):
    """Retain one private input in this process while discovery retries twice."""
    for attempt in range(1, 4):
        try:
            return verify(key)
        except SetupError as exc:
            retryable = exc.code in ('network_error', 'unexpected_response') or (
                exc.code == 'service_unavailable' and exc.details.get('http_status') in (
                    None, 408, 425, 429, 500, 502, 503, 504))
            delay = max(attempt, exc.details.get('retry_after_seconds', 0))
            if delay > 30 or exc.details.get('retry_after_unavailable'):
                retryable = False
            if not retryable or attempt == 3:
                if retryable:
                    raise SetupError(exc.code, **{**exc.details, 'attempts': attempt}) from None
                raise
            if report:
                report({'status': 'retrying_verification', 'attempt': attempt + 1,
                        'max_attempts': 3, 'retry_after_seconds': delay, 'code': exc.code})
            time.sleep(delay)


def setup_client(client, path, read_key=read_key, verify=verify_key, replace=False, check=False, report=None):
    path = Path(path)
    if path.is_symlink():
        raise SetupError('config_symlink')
    raw = path.read_text(encoding='utf-8') if path.exists() else ''
    _, entry = parse_config(client, raw)
    # Fail on an unsupported layout before asking the user for a credential.
    if not check:
        new_config(client, raw, 'configuration-preflight')
    key = saved_key(client, entry)
    if key and not replace:
        try:
            verify_with_retry(key, verify, report)
        except SetupError as exc:
            if check or exc.code not in ('invalid_key', 'invalid_input', 'key_revoked'):
                raise
            key = None
        else:
            if check:
                return {'status': 'credential_verified', 'configuration_saved': False,
                        'reload_required': False, 'client_connection_verified': False,
                        'next_action': 'discover_client_tools'}
            content = new_config(client, raw, clean_key(key))
            current, _ = parse_config(client, raw)
            rewritten, _ = parse_config(client, content)
            if current == rewritten:
                private_permissions(path)
                return {'status': 'credential_verified', 'configuration_saved': False,
                        'reload_required': False, 'client_connection_verified': False,
                        'next_action': 'discover_client_tools'}
    if check:
        raise SetupError('key_missing')
    if not key or replace:
        prepare_config_write(path)
        key = clean_key(read_key())
        verify_with_retry(key, verify, report)
    content = new_config(client, raw, key)
    save_config(path, raw, content)
    return {'status': 'credential_verified', 'configuration_saved': True,
            'reload_required': None, 'client_connection_verified': False,
            'next_action': 'discover_client_tools'}


def default_config(client, home=None, platform=None, environ=None):
    """Resolve user-scoped files; extensions need an existing, unambiguous file."""
    client_profile(client)
    home = Path.home() if home is None else Path(home)
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ
    if client == 'codex':
        return Path(environ.get('CODEX_HOME') or home / '.codex') / 'config.toml'
    if client == 'claude-code':
        if environ.get('CLAUDE_CONFIG_DIR'):
            raise SetupError('custom_config')
        return home / '.claude.json'
    if client == 'copilot-cli':
        return Path(environ.get('COPILOT_HOME') or home / '.copilot') / 'mcp-config.json'
    if platform == 'darwin':
        app_root = home / 'Library/Application Support'
    elif platform == 'win32':
        app_root = Path(environ.get('APPDATA') or home / 'AppData/Roaming')
    else:
        app_root = Path(environ.get('XDG_CONFIG_HOME') or home / '.config')
    def select_existing(candidates, fallback=None):
        existing = [path for path in candidates if path.is_file()]
        if len(existing) > 1 or (not existing and fallback is None):
            raise SetupError('config_selection_required')
        return existing[0] if existing else fallback
    def has_profiles(user):
        profiles = user / 'profiles'
        return profiles.is_dir() and any(path.is_dir() for path in profiles.iterdir())
    if client == 'vscode':
        if environ.get('VSCODE_PORTABLE'):
            user = Path(environ['VSCODE_PORTABLE']) / 'user-data/User'
            if has_profiles(user):
                raise SetupError('config_selection_required')
            return user / 'mcp.json'
        users = [app_root / editor / 'User' for editor in ('Code', 'Code - Insiders')]
        if sum(user.is_dir() for user in users) > 1 or any(has_profiles(user) for user in users):
            raise SetupError('config_selection_required')
        candidates = [user / 'mcp.json' for user in users]
        installed = [user for user in users if user.is_dir()]
        fallback = (installed[0] if installed else app_root / 'Code/User') / 'mcp.json'
        return select_existing(candidates, fallback)
    if client == 'windsurf':
        legacy = home / '.codeium/windsurf/mcp_config.json'
        devin_root = app_root if platform == 'win32' else Path(environ.get('XDG_CONFIG_HOME') or home / '.config')
        relocated = devin_root / 'devin/mcp_config.json'
        if legacy.parent.is_dir() and relocated.parent.is_dir():
            raise SetupError('config_selection_required')
        return select_existing([legacy, relocated], relocated if relocated.parent.is_dir() else legacy)
    if client in ('cline', 'roo-code'):
        if client == 'cline' and environ.get('CLINE_MCP_SETTINGS_PATH'):
            return Path(environ['CLINE_MCP_SETTINGS_PATH']).expanduser()
        extension, filename = ('saoudrizwan.claude-dev', 'cline_mcp_settings.json') if client == 'cline' else ('rooveterinaryinc.roo-cline', 'mcp_settings.json')
        users = [app_root / editor / 'User' for editor in ('Code', 'Code - Insiders', 'Cursor', 'Windsurf', 'VSCodium')]
        if sum(user.is_dir() for user in users) > 1 or any(has_profiles(user) for user in users):
            raise SetupError('config_selection_required')
        candidates = [user / 'globalStorage' / extension / 'settings' / filename for user in users]
        if client == 'cline':
            cli = home / '.cline/data/settings/cline_mcp_settings.json'
            if cli.is_file() and any(user.is_dir() for user in users):
                raise SetupError('config_selection_required')
            candidates.append(cli)
        return select_existing(candidates)
    return home / {
        'workbuddy': '.workbuddy/mcp.json',
        'cursor': '.cursor/mcp.json',
        'gemini-cli': '.gemini/settings.json',
    }[client]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client', required=True, choices=tuple(CLIENTS))
    parser.add_argument('--input', default='auto', choices=('auto', 'terminal', 'env'))
    parser.add_argument('--language', choices=('en', 'zh'), default='en')
    parser.add_argument('--transport', choices=('auto', 'curl', 'urllib'), default='auto')
    parser.add_argument('--config', type=Path, help='Explicit user configuration path for custom profiles')
    parser.add_argument('--replace', action='store_true', help='Replace this connection credential using local input')
    parser.add_argument('--check', action='store_true', help='Verify the saved credential without prompting or writing')
    args = parser.parse_args()
    try:
        if args.config:
            path = args.config.expanduser()
        else:
            path = default_config(args.client)
        result = setup_client(args.client, path, read_key=lambda: read_key(args.input, args.language),
                              verify=lambda key: verify_key(key, transport=args.transport),
                              replace=args.replace, check=args.check,
                              report=lambda status: print(json.dumps(status), flush=True))
        result['client'] = args.client
        print(json.dumps(result))
        return 0
    except SetupError as exc:
        print(json.dumps({'status': 'error', 'code': exc.code, 'message': str(exc), **exc.details}))
    except PermissionError:
        print(json.dumps({'status': 'error', 'code': 'permission_required', 'message': ERRORS['permission_required']}))
    except KeyboardInterrupt:
        print(json.dumps({'status': 'error', 'code': 'cancelled', 'message': ERRORS['cancelled']}))
    except Exception:
        # Never include raw exceptions: HTTP errors and parser errors can contain secrets.
        print(json.dumps({'status': 'error', 'code': 'io_error', 'message': ERRORS['io_error']}))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
