"""Bounded HTTP transport for the official endpoint; credentials stay off argv."""
from email.parser import BytesParser
import io
from http.client import IncompleteRead
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from urllib.error import HTTPError, URLError

ENDPOINT = 'https://videotranscriber.ai/mcp'
MAX_BYTES = 16 * 1024 * 1024
HEADER_LIMIT = 64 * 1024


class ResponseTooLarge(ValueError):
    pass


class CurlTransferError(URLError):
    def __init__(self, code):
        self.curl_exit_code = code
        super().__init__('curl_transfer_failed')


def read_complete(response, limit, timeout=45):
    """Collect short reads and reject EOF before the advertised byte count."""
    length = response.headers.get('Content-Length')
    if length is not None:
        if not isinstance(length, str) or not length.isascii() or not length.isdigit():
            raise ValueError('invalid_content_length')
        length = int(length)
        if length > limit:
            raise ResponseTooLarge()
    chunks = []
    size = 0
    deadline = time.monotonic() + timeout
    while length is None or size < length:
        if time.monotonic() > deadline:
            raise TimeoutError()
        chunk = response.read(min(65536, limit + 1 - size))
        if not chunk:
            break
        chunks.append(chunk)
        size += len(chunk)
        if size > limit:
            raise ResponseTooLarge()
    if length is not None and size < length:
        raise IncompleteRead(b'', length - size)
    return b''.join(chunks)


def quoted(value):
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"').replace('\r', '\\r').replace('\n', '\\n') + '"'


class CurlResponse(io.BytesIO):
    def __init__(self, body, status, headers):
        super().__init__(body)
        self.status = status
        self.headers = headers


def response_parts(raw, pending=False):
    consumed = 0
    while True:
        header, separator, body = raw.partition(b'\r\n\r\n')
        if len(header) + consumed > HEADER_LIMIT:
            raise URLError('invalid_response_headers')
        if not separator:
            if pending:
                return None
            raise URLError('invalid_response_headers')
        first, _, fields = header.partition(b'\r\n')
        match = re.fullmatch(rb'HTTP/\S+ ([0-9]{3})(?: .*)?', first)
        if not match:
            raise URLError('invalid_response_status')
        status = int(match[1])
        headers = BytesParser().parsebytes(fields + b'\r\n\r\n')
        if 100 <= status < 200:
            consumed += len(header) + len(separator)
            raw = body
            continue
        return status, headers, body


def matching_event(body, request_id):
    if request_id is None:
        return False
    for event in body.replace(b'\r\n', b'\n').split(b'\n\n')[:-1]:
        data = [line[5:].lstrip(b' ') for line in event.split(b'\n') if line.startswith(b'data:')]
        if not data:
            continue
        try:
            payload = json.loads(b'\n'.join(data))
        except (ValueError, UnicodeError):
            continue
        if isinstance(payload, dict) and payload.get('id') == request_id:
            return True
    return False


def stop_process(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=1)
    else:
        process.wait(timeout=1)


class CurlOpener:
    def __init__(self, executable):
        self.executable = executable

    def open(self, request, timeout):
        if request.full_url != ENDPOINT or request.get_method() != 'POST':
            raise ValueError('endpoint_rejected')
        config = ['url = ' + quoted(ENDPOINT), 'request = "POST"',
                  'silent', 'show-error', 'no-buffer', 'suppress-connect-headers',
                  'proto = "=https"', 'max-redirs = 0',
                  'connect-timeout = 10', 'max-time = ' + str(timeout),
                  'max-filesize = ' + str(MAX_BYTES), 'dump-header = "-"']
        for name, value in request.header_items():
            if any(char in name + value for char in '\r\n'):
                raise ValueError('invalid_header')
            config.append('header = ' + quoted(name + ': ' + value))
        config.append('data-binary = ' + quoted((request.data or b'').decode('utf-8')))
        # The config (including Authorization) is piped, never a file or argv.
        # Response data uses an automatically removed private temporary file.
        raw = self.collect(('\n'.join(config) + '\n').encode(),
                           json.loads(request.data or b'{}').get('id'), timeout)
        status, headers, body = response_parts(raw)
        response = CurlResponse(body, status, headers)
        if status >= 300:
            raise HTTPError(ENDPOINT, status, 'MCP HTTP error', headers, response)
        return response

    def collect(self, config, request_id, timeout):
        process = None
        response_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w+b', buffering=0, delete=False) as output:
                response_path = output.name
                process = subprocess.Popen([self.executable, '-q', '--config', '-'],
                    stdin=subprocess.PIPE, stdout=output, stderr=subprocess.DEVNULL)
                try:
                    process.stdin.write(config)
                finally:
                    process.stdin.close()
                deadline = time.monotonic() + timeout + 5
                # A distinct reader avoids changing the child's shared file offset.
                with open(response_path, 'rb') as reader:
                    while True:
                        reader.seek(0)
                        raw = reader.read(MAX_BYTES + HEADER_LIMIT + 1)
                        if len(raw) > MAX_BYTES + HEADER_LIMIT:
                            raise ResponseTooLarge()
                        parts = response_parts(raw, pending=True)
                        if parts:
                            status, headers, body = parts
                            if (200 <= status < 300 and 'text/event-stream' in headers.get('Content-Type', '').lower()
                                    and matching_event(body, request_id)):
                                return raw
                        code = process.poll()
                        if code is not None:
                            if code:
                                raise CurlTransferError(code)
                            reader.seek(0)
                            raw = reader.read(MAX_BYTES + HEADER_LIMIT + 1)
                            if len(raw) > MAX_BYTES + HEADER_LIMIT:
                                raise ResponseTooLarge()
                            return raw
                        if time.monotonic() >= deadline:
                            raise URLError(TimeoutError())
                        time.sleep(0.05)
        finally:
            try:
                if process is not None:
                    stop_process(process)
            finally:
                if response_path is not None:
                    try:
                        os.unlink(response_path)
                    except FileNotFoundError:
                        pass


def default_opener(transport, factory):
    executable = shutil.which('curl') if transport != 'urllib' else None
    if executable:
        return CurlOpener(executable)
    if transport == 'curl':
        raise URLError(OSError('curl_unavailable'))
    return factory()
