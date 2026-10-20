"""Recovery behavior: one local paste, bounded discovery, no forced reload."""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/setup-videotranscriber/scripts/configure_client.py'
KEY = 'vs_test_recovery_dummy_credential'


class SetupRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('recovery_helper', SCRIPT)
        cls.helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.helper)

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.config = Path(self.folder.name) / 'config.toml'

    def test_transient_validation_failures_reuse_one_private_input(self):
        inputs = []
        attempts = []
        updates = []
        def read_key():
            inputs.append(True)
            return KEY
        def verify(key):
            self.assertEqual(key, KEY)
            self.assertFalse(self.config.exists())
            attempts.append(True)
            if len(attempts) == 1:
                raise self.helper.SetupError('network_error', operation='initialize')
            if len(attempts) == 2:
                raise self.helper.SetupError('unexpected_response', operation='tools/list')
        with patch.object(self.helper.time, 'sleep'):
            result = self.helper.setup_client('codex', self.config, read_key=read_key,
                                              verify=verify, report=updates.append)
        self.assertEqual(len(inputs), 1)
        self.assertEqual(len(attempts), 3)
        self.assertEqual([item['attempt'] for item in updates], [2, 3])
        self.assertNotIn(KEY, json.dumps(updates))
        self.assertTrue(result['configuration_saved'])
        self.assertIsNone(result['reload_required'])
        self.assertEqual(result['next_action'], 'discover_client_tools')
        self.assertIn(KEY, self.config.read_text())

    def test_persistent_network_failure_stops_without_writing_or_reprompting(self):
        self.config.write_text('model = "keep"\n')
        original = self.config.read_bytes()
        inputs = []
        attempts = []
        def read_key():
            inputs.append(True)
            return KEY
        def verify(key):
            attempts.append(True)
            raise self.helper.SetupError('network_error', operation='initialize')
        with patch.object(self.helper.time, 'sleep'), self.assertRaises(self.helper.SetupError) as caught:
            self.helper.setup_client('codex', self.config, read_key=read_key, verify=verify)
        self.assertEqual(len(inputs), 1)
        self.assertEqual(len(attempts), 3)
        self.assertEqual(caught.exception.details['attempts'], 3)
        self.assertEqual(self.config.read_bytes(), original)
        self.assertNotIn(KEY, str(caught.exception))

    def test_saved_key_transient_failure_never_opens_another_input(self):
        self.config.write_text(self.helper.new_config('codex', '', KEY))
        original = self.config.read_bytes()
        attempts = []
        def verify(key):
            attempts.append(True)
            if len(attempts) == 1:
                raise self.helper.SetupError('network_error')
        with patch.object(self.helper.time, 'sleep'):
            result = self.helper.setup_client('codex', self.config,
                read_key=lambda: self.fail('Saved credential should be reused'), verify=verify)
        self.assertEqual(len(attempts), 2)
        self.assertFalse(result['configuration_saved'])
        self.assertEqual(result['next_action'], 'discover_client_tools')
        self.assertEqual(self.config.read_bytes(), original)

    def test_permanent_errors_are_not_retried(self):
        for code in ('invalid_key', 'key_revoked', 'account_disabled', 'access_blocked',
                     'redirect_rejected', 'permission_required'):
            attempts = []
            def verify(key):
                attempts.append(True)
                raise self.helper.SetupError(code)
            with (self.subTest(code=code), patch.object(self.helper.time, 'sleep') as sleep,
                  self.assertRaises(self.helper.SetupError) as caught):
                self.helper.setup_client('codex', self.config, read_key=lambda: KEY, verify=verify)
            self.assertEqual(caught.exception.code, code)
            self.assertEqual(len(attempts), 1)
            sleep.assert_not_called()
            self.assertFalse(self.config.exists())

    def test_write_permission_is_checked_before_private_input(self):
        self.config.write_text('model = "keep"\n')
        with (patch.object(self.helper.tempfile, 'mkstemp', side_effect=PermissionError()),
              self.assertRaises(self.helper.SetupError) as caught):
            self.helper.setup_client('codex', self.config,
                read_key=lambda: self.fail('Permission must be checked before asking for a Key'),
                verify=lambda key: None)
        self.assertEqual(caught.exception.code, 'permission_required')
        self.assertEqual(self.config.read_text(), 'model = "keep"\n')

    def test_unexpected_response_reports_safe_phase_details(self):
        class Response(io.BytesIO):
            headers = {'Content-Type': 'text/html'}
            status = 200
        class Transport:
            def open(self, request, timeout):
                return Response(('<html>' + KEY + '</html>').encode())
        with self.assertRaises(self.helper.SetupError) as caught:
            self.helper.verify_key(KEY, opener=Transport())
        self.assertEqual(caught.exception.code, 'unexpected_response')
        self.assertEqual(caught.exception.details['operation'], 'initialize')
        self.assertEqual(caught.exception.details['http_status'], 200)
        self.assertEqual(caught.exception.details['content_type'], 'text/html')
        self.assertNotIn(KEY, json.dumps(caught.exception.details))

    def test_network_permission_error_is_distinguished_from_transient_failure(self):
        class Transport:
            def open(self, request, timeout):
                raise URLError(PermissionError('blocked'))
        with self.assertRaises(self.helper.SetupError) as caught:
            self.helper.verify_key(KEY, opener=Transport())
        self.assertEqual(caught.exception.code, 'permission_required')
        self.assertEqual(caught.exception.details['operation'], 'initialize')

    def test_nonretryable_service_status_does_not_repeat_a_bad_request(self):
        attempts = []
        def verify(key):
            attempts.append(True)
            raise self.helper.SetupError('service_unavailable', http_status=400)
        with (patch.object(self.helper.time, 'sleep') as sleep,
              self.assertRaises(self.helper.SetupError)):
            self.helper.setup_client('codex', self.config, read_key=lambda: KEY, verify=verify)
        self.assertEqual(len(attempts), 1)
        sleep.assert_not_called()

    def test_service_backoff_is_respected_without_another_key_input(self):
        attempts = []
        def verify(key):
            attempts.append(True)
            if len(attempts) == 1:
                raise self.helper.SetupError('service_unavailable', http_status=503, retry_after_seconds=3)
        with patch.object(self.helper.time, 'sleep') as sleep:
            self.helper.setup_client('codex', self.config, read_key=lambda: KEY, verify=verify)
        self.assertEqual(len(attempts), 2)
        sleep.assert_called_once_with(3)

    def test_long_service_backoff_is_reported_without_an_early_retry(self):
        attempts = []
        def verify(key):
            attempts.append(True)
            raise self.helper.SetupError('service_unavailable', http_status=503, retry_after_seconds=120)
        with (patch.object(self.helper.time, 'sleep') as sleep,
              self.assertRaises(self.helper.SetupError) as caught):
            self.helper.setup_client('codex', self.config, read_key=lambda: KEY, verify=verify)
        self.assertEqual(caught.exception.details['retry_after_seconds'], 120)
        self.assertEqual(len(attempts), 1)
        sleep.assert_not_called()

    def test_http_date_backoff_does_not_trigger_an_early_retry(self):
        attempts = []
        class Transport:
            def open(inner, request, timeout):
                attempts.append(True)
                from urllib.error import HTTPError
                raise HTTPError('https://videotranscriber.ai/mcp', 503, 'unavailable',
                    {'Retry-After': 'Thu, 01 Jan 1970 00:02:00 GMT'}, io.BytesIO(b'{}'))
        with (patch.object(self.helper.time, 'time', return_value=0),
              patch.object(self.helper.time, 'sleep') as sleep,
              self.assertRaises(self.helper.SetupError) as caught):
            self.helper.setup_client('codex', self.config, read_key=lambda: KEY,
                verify=lambda key: self.helper.verify_key(key, opener=Transport()))
        self.assertEqual(caught.exception.details['retry_after_seconds'], 120)
        self.assertEqual(len(attempts), 1)
        sleep.assert_not_called()

    def test_unreadable_backoff_is_not_echoed_or_ignored(self):
        attempts = []
        class Transport:
            def open(inner, request, timeout):
                attempts.append(True)
                from urllib.error import HTTPError
                raise HTTPError('https://videotranscriber.ai/mcp', 503, 'unavailable',
                    {'Retry-After': KEY}, io.BytesIO(b'{}'))
        with (patch.object(self.helper.time, 'sleep') as sleep,
              self.assertRaises(self.helper.SetupError) as caught):
            self.helper.setup_client('codex', self.config, read_key=lambda: KEY,
                verify=lambda key: self.helper.verify_key(key, opener=Transport()))
        self.assertEqual(len(attempts), 1)
        self.assertNotIn(KEY, json.dumps(caught.exception.details))
        sleep.assert_not_called()


if __name__ == '__main__':
    unittest.main()
