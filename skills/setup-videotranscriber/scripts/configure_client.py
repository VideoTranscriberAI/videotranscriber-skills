#!/usr/bin/env python3
"""Configure a local Codex or Claude Code connection without exposing the Key to chat.

Requires Python 3.11+. No third-party packages. This command never creates a
transcription. Credentials are stored in the client's plaintext user config.
"""

import argparse
import csv
import getpass
import io
import json
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


ENDPOINT = 'https://videotranscriber.ai/mcp'
TOOLS = {'create_transcription', 'get_transcription', 'get_transcription_result'}
ERRORS = {
    'cancelled': 'Cancelled; the existing configuration was kept.',
    'invalid_key': 'The Key was rejected. Create or copy an active API Key and try again.',
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
    'permission_failed': 'Private file permissions could not be set; no new configuration was saved.',
    'io_error': 'The local configuration could not be saved; check filesystem permissions.',
}


class SetupError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(ERRORS[code])


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SetupError('redirect_rejected')


def clean_key(value):
    value = value.strip()
    if not value or len(value) > 4096 or any(ord(char) < 33 or ord(char) > 126 for char in value) or '${' in value:
        raise SetupError('invalid_input')
    return value


def response_payload(response, request_id):
    if 'text/event-stream' not in response.headers.get('Content-Type', '').lower():
        raw = response.read(262145)
        if not raw or len(raw) > 262144:
            raise SetupError('unexpected_response')
        return json.loads(raw)
    # A valid SSE connection can remain open. Stop after this request's event.
    total = 0
    data = []
    deadline = time.monotonic() + 10
    while total < 262144 and time.monotonic() < deadline:
        line = response.readline(262145 - total)
        if not line:
            break
        total += len(line)
        line = line.decode('utf-8').rstrip('\r\n')
        if line.startswith('data:'):
            data.append(line[5:].lstrip(' '))
        elif not line and data:
            payload = json.loads('\n'.join(data))
            data = []
            if isinstance(payload, dict) and payload.get('id') == request_id:
                return payload
    raise SetupError('unexpected_response')


def verify_key(key, opener=None):
    """Use authenticated MCP initialization and tool discovery, never tools/call."""
    key = clean_key(key)
    transport = opener or build_opener(NoRedirect())
    headers = {'Authorization': 'Bearer ' + key, 'Accept': 'application/json, text/event-stream',
               'Content-Type': 'application/json'}

    def request(method, request_id=None, params=None):
        body = {'jsonrpc': '2.0', 'method': method}
        if request_id is not None:
            body['id'] = request_id
        if params is not None:
            body['params'] = params
        req = Request(ENDPOINT, data=json.dumps(body).encode(), headers=headers, method='POST')
        try:
            with transport.open(req, timeout=10) as response:
                if response.headers.get('Mcp-Session-Id'):
                    session = response.headers['Mcp-Session-Id']
                    if not session or any(ord(char) < 33 or ord(char) > 126 for char in session):
                        raise SetupError('unexpected_response')
                    headers['Mcp-Session-Id'] = session
                if request_id is None:
                    return None
                payload = response_payload(response, request_id)
            if (not isinstance(payload, dict) or payload.get('id') != request_id
                    or not isinstance(payload.get('result'), dict) or 'error' in payload):
                raise SetupError('unexpected_response')
            return payload['result']
        except HTTPError as exc:
            code = 'invalid_key' if exc.code in (401, 403) else 'service_unavailable'
            exc.close()
            raise SetupError(code) from None
        except (URLError, TimeoutError, OSError):
            raise SetupError('network_error') from None
        except (ValueError, TypeError, UnicodeError):
            raise SetupError('unexpected_response') from None

    result = request('initialize', 1, {'protocolVersion': '2025-03-26',
        'capabilities': {}, 'clientInfo': {'name': 'videotranscriber-local-setup', 'version': '1.0'}})
    protocol = result.get('protocolVersion')
    if not isinstance(protocol, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', protocol):
        raise SetupError('unexpected_response')
    headers['MCP-Protocol-Version'] = protocol
    request('notifications/initialized')
    result = request('tools/list', 2)
    tools = result.get('tools')
    if not isinstance(tools, list) or not TOOLS.issubset({item.get('name') for item in tools
            if isinstance(item, dict) and isinstance(item.get('name'), str)}):
        raise SetupError('unexpected_response')


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


def connection_name(client, data):
    servers = data.get('mcp_servers' if client == 'codex' else 'mcpServers', {})
    if not isinstance(servers, dict):
        raise SetupError('config_invalid')
    matches = [name for name, entry in servers.items() if isinstance(entry, dict)
               and isinstance(entry.get('url'), str) and entry['url'].rstrip('/') == ENDPOINT]
    if len(matches) > 1:
        raise SetupError('ambiguous_connection')
    if 'videotranscriber' in servers:
        return 'videotranscriber'
    return matches[0] if matches else 'videotranscriber'


def parse_config(client, raw):
    try:
        data = tomllib.loads(raw) if client == 'codex' else json.loads(raw or '{}')
        if not isinstance(data, dict):
            raise ValueError()
        servers = data.get('mcp_servers' if client == 'codex' else 'mcpServers', {})
        name = connection_name(client, data)
        if not isinstance(servers.get(name, {}), dict):
            raise ValueError()
        entry = servers.get(name, {})
        if entry and entry.get('url', '').rstrip('/') != ENDPOINT:
            raise SetupError('config_conflict')
        return data, entry
    except (ValueError, TypeError, AttributeError):
        raise SetupError('config_invalid') from None


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
    name = connection_name(client, data)
    entry = dict(existing)
    header_field = 'http_headers' if client == 'codex' else 'headers'
    headers = entry.get(header_field, {})
    if not isinstance(headers, dict):
        raise SetupError('config_invalid')
    headers = {name: value for name, value in headers.items() if name.lower() != 'authorization'}
    headers['Authorization'] = 'Bearer ' + key
    entry.update({'url': ENDPOINT, header_field: headers})
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
    entry.pop('headersHelper', None)
    entry['type'] = 'http'
    data['mcpServers'] = {**data.get('mcpServers', {}), name: entry}
    return json.dumps(data, indent=2, ensure_ascii=False) + '\n'


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


def setup_client(client, path, read_key=read_key, verify=verify_key, replace=False, check=False):
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
            verify(key)
        except SetupError as exc:
            if check or exc.code not in ('invalid_key', 'invalid_input'):
                raise
            key = None
        else:
            if check:
                return {'status': 'credential_verified', 'configuration_saved': False,
                        'reload_required': False, 'client_connection_verified': False}
            content = new_config(client, raw, clean_key(key))
            current, _ = parse_config(client, raw)
            rewritten, _ = parse_config(client, content)
            if current == rewritten:
                private_permissions(path)
                return {'status': 'credential_verified', 'configuration_saved': False,
                        'reload_required': False, 'client_connection_verified': False}
    if check:
        raise SetupError('key_missing')
    if not key or replace:
        key = clean_key(read_key())
        verify(key)
    content = new_config(client, raw, key)
    save_config(path, raw, content)
    return {'status': 'credential_verified', 'configuration_saved': True,
            'reload_required': True, 'client_connection_verified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client', required=True, choices=('codex', 'claude-code'))
    parser.add_argument('--input', default='auto', choices=('auto', 'terminal', 'env'))
    parser.add_argument('--language', choices=('en', 'zh'), default='en')
    parser.add_argument('--config', type=Path, help='Explicit user configuration path for custom profiles')
    parser.add_argument('--replace', action='store_true', help='Replace this connection credential using local input')
    parser.add_argument('--check', action='store_true', help='Verify the saved credential without prompting or writing')
    args = parser.parse_args()
    try:
        if args.config:
            path = args.config.expanduser()
        elif args.client == 'codex':
            path = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'config.toml'
        elif os.environ.get('CLAUDE_CONFIG_DIR'):
            raise SetupError('custom_config')
        else:
            path = Path.home() / '.claude.json'
        result = setup_client(args.client, path, read_key=lambda: read_key(args.input, args.language),
                              replace=args.replace, check=args.check)
        result['client'] = args.client
        print(json.dumps(result))
        return 0
    except SetupError as exc:
        print(json.dumps({'status': 'error', 'code': exc.code, 'message': str(exc)}))
    except KeyboardInterrupt:
        print(json.dumps({'status': 'error', 'code': 'cancelled', 'message': ERRORS['cancelled']}))
    except Exception:
        # Never include raw exceptions: HTTP errors and parser errors can contain secrets.
        print(json.dumps({'status': 'error', 'code': 'io_error', 'message': ERRORS['io_error']}))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
