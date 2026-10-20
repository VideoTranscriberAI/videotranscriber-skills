#!/usr/bin/env python3
"""Call one official MCP transcription tool using the active client's saved Key."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

spec = importlib.util.spec_from_file_location('videotranscriber_setup', Path(__file__).with_name('configure_client.py'))
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)

CREATE_FIELDS = {'source_url', 'idempotency_key', 'language', 'transcription_model',
                 'speaker_diarization', 'include_audio_events', 'cleanup_speech',
                 'keyterms', 'chapters', 'target_language'}


def validate_arguments(tool, arguments):
    if tool not in helper.TOOLS or not isinstance(arguments, dict):
        raise helper.SetupError('invalid_arguments')
    if tool == 'create_transcription':
        key = arguments.get('idempotency_key')
        source = arguments.get('source_url')
        if (set(arguments) - CREATE_FIELDS or not isinstance(key, str)
                or not re.fullmatch(r'[!-~]{1,128}', key)
                or not isinstance(source, str) or len(source) > 4096
                or not re.match(r'^https?://[^/\s]+', source)):
            raise helper.SetupError('invalid_arguments')
    elif (set(arguments) != {'request_id'} or not isinstance(arguments['request_id'], str)
          or not re.fullmatch(r'req_[0-9a-f]{32}', arguments['request_id'])):
        raise helper.SetupError('invalid_arguments')


def result_payload(result):
    if not isinstance(result, dict):
        raise helper.SetupError('unexpected_response', operation='tools/call')
    payload = result.get('structuredContent')
    if not isinstance(payload, dict):
        content = result.get('content', [])
        texts = [item.get('text') for item in content if isinstance(item, dict) and item.get('type') == 'text']
        try:
            payload = json.loads(texts[0]) if len(texts) == 1 else None
        except (ValueError, TypeError):
            payload = None
    if not isinstance(payload, dict):
        if result.get('isError') is True:
            message = '\n'.join(item for item in texts if isinstance(item, str))[:4096]
            return {'error': {'code': 'mcp_tool_error', 'message': message or 'The MCP tool rejected this operation.'}}
        raise helper.SetupError('unexpected_response', operation='tools/call', failure_stage='tool_payload')
    return payload


def private_result(value, key, include_download_links):
    if isinstance(value, dict):
        return {name: ('[download link omitted]' if not include_download_links
                       and name.lower() in ('url', 'download_url', 'srt_url', 'vtt_url', 'txt_url')
                       and isinstance(item, str) and item.startswith(('https://', 'http://'))
                       else private_result(item, key, include_download_links))
                for name, item in value.items()}
    if isinstance(value, list):
        return [private_result(item, key, include_download_links) for item in value]
    if isinstance(value, str):
        return value.replace(key, '[credential omitted]')
    return value


def run_tool(client, path, tool, arguments, opener=None, transport='auto',
             report=None, include_download_links=False):
    validate_arguments(tool, arguments)
    path = Path(path)
    if path.is_symlink():
        raise helper.SetupError('config_symlink')
    _, entry = helper.parse_config(client, path.read_text() if path.exists() else '')
    if entry and helper.endpoint(entry) != helper.ENDPOINT:
        raise helper.SetupError('config_conflict')
    key = helper.saved_key(client, entry)
    if not key:
        raise helper.SetupError('key_missing')
    rpc = helper.verify_with_retry(key, lambda credential: helper.mcp_connection(
        credential, opener=opener, transport=transport, max_bytes=16 * 1024 * 1024, timeout=45), report)
    # The same tool, arguments and JSON-RPC ID are retained for every retry.
    def invoke(credential):
        result = rpc('tools/call', 3, {'name': tool, 'arguments': arguments})
        return result, result_payload(result)
    call_report = (lambda update: report({**update, 'status': 'retrying_mcp_call'})) if report else None
    result, payload = helper.verify_with_retry(key, invoke, call_report)
    metadata = result.get('_meta') if isinstance(result.get('_meta'), dict) else {}
    status = metadata.get('http_status')
    failed = result.get('isError') is True or payload.get('error') is not None or (isinstance(status, int) and status >= 400)
    retry_after = metadata.get('retry_after')
    if not (isinstance(retry_after, int) and retry_after >= 0 or
            isinstance(retry_after, str) and retry_after.isascii() and retry_after.isdigit() and len(retry_after) <= 8):
        retry_after = None
    return {'status': 'tool_error' if failed else 'completed', 'tool': tool,
            'http_status': status if isinstance(status, int) else None,
            'retry_after': retry_after,
            'result': private_result(payload, key, include_download_links)}


def write_result(path, result):
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise helper.SetupError('output_exists') from None
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as output:
            helper.private_permissions(path)
            json.dump(result, output, ensure_ascii=False)
            output.write('\n')
    except Exception:
        path.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--client', required=True, choices=tuple(helper.CLIENTS))
    parser.add_argument('--config', type=Path)
    parser.add_argument('--tool', required=True, choices=sorted(helper.TOOLS))
    parser.add_argument('--arguments', required=True, help='Tool JSON only; never a credential')
    parser.add_argument('--transport', choices=('auto', 'curl', 'urllib'), default='auto')
    parser.add_argument('--include-download-links', action='store_true', help='Only for an explicit subtitle/download request')
    parser.add_argument('--output', type=Path, help='New private JSON file for get_transcription_result; never overwrite')
    args = parser.parse_args()
    try:
        try:
            arguments = json.loads(args.arguments)
        except ValueError:
            raise helper.SetupError('invalid_arguments') from None
        if args.output:
            if args.tool != 'get_transcription_result':
                raise helper.SetupError('invalid_arguments')
            args.output = args.output.expanduser().absolute()
            if args.output.exists() or args.output.is_symlink():
                raise helper.SetupError('output_exists')
        result = run_tool(args.client, args.config.expanduser() if args.config else helper.default_config(args.client),
            args.tool, arguments, transport=args.transport, include_download_links=args.include_download_links,
            report=lambda status: print(json.dumps(status), flush=True))
        if args.output:
            write_result(args.output, result)
            print(json.dumps({'status': result['status'], 'tool': args.tool,
                'http_status': result.get('http_status'), 'result_file': str(args.output),
                'request_id': arguments['request_id']}, ensure_ascii=False))
        else:
            print(json.dumps(result, ensure_ascii=False))
        return 2 if result['status'] == 'tool_error' else 0
    except helper.SetupError as exc:
        print(json.dumps({'status': 'error', 'code': exc.code, 'message': str(exc), **exc.details}))
    except PermissionError:
        print(json.dumps({'status': 'error', 'code': 'permission_required'}))
    except KeyboardInterrupt:
        print(json.dumps({'status': 'error', 'code': 'cancelled'}))
    except Exception:
        print(json.dumps({'status': 'error', 'code': 'io_error'}))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
