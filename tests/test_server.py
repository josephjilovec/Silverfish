from dataclasses import replace
import hashlib
import hmac
import http.client
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import time
import unittest

from silvertrap.config import Config
from silvertrap.server import Server
from silvertrap.service import Service


class APITest(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.token = 'test-access-' + 'x'*32
        self.secret = 'intake-test-secret-' + 'y'*32
        self.service = Service(Config(Path(self.tmp.name), operator_token=self.token, webhook_secret=self.secret))
        self.server = Server(('127.0.0.1', 0), self.service)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.service.store.close()
        self.tmp.cleanup()

    def request(self, path, method='GET', body=None, headers=None, authenticated=True):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        actual = {'Authorization':'Bearer '+self.token} if authenticated else {}
        if body is not None:
            actual['Content-Type'] = 'application/json'
        actual.update(headers or {})
        conn.request(method, path, body=body, headers=actual)
        response = conn.getresponse()
        result = response.status, response.read(), dict(response.getheaders())
        conn.close()
        return result

    def test_auth_required_for_every_evidence_route(self):
        for path in ['/api/overview', '/api/cases', '/api/indicators', '/api/events']:
            self.assertEqual(self.request(path, authenticated=False)[0], 401)
        self.assertEqual(self.request('/api/overview')[0], 200)

    def test_static_is_sandboxed_and_not_a_file_browser(self):
        response = self.request('/', authenticated=False)
        self.assertEqual(response[0], 200)
        self.assertIn("frame-ancestors 'none'", response[2]['Content-Security-Policy'])
        self.assertNotEqual(self.request('/../../etc/passwd')[0], 200)
        self.assertEqual(self.request('/app.js', authenticated=False)[0], 200)

    def test_cross_origin_is_rejected(self):
        self.assertEqual(self.request('/api/overview', headers={'Origin':'https://other.invalid'})[0], 403)

    def test_api_create_ingest_export_and_simulate(self):
        status, raw, _ = self.request('/api/cases', 'POST', json.dumps({'scenario':'tech-support'}))
        self.assertEqual(status, 201)
        case_id = json.loads(raw)['id']
        status, raw, _ = self.request(f'/api/cases/{case_id}/simulate', 'POST', '{"all_steps":true}')
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(raw)['messages']), 10)
        status, raw, headers = self.request(f'/api/cases/{case_id}/export.json')
        self.assertEqual(status, 200)
        self.assertIn('attachment;', headers['Content-Disposition'])
        self.assertEqual(json.loads(raw)['schema'], 'silvertrap.evidence.v1')

    def test_intake_signature_replay_and_expiry(self):
        c = self.service.create_case()
        payload = json.dumps({'case_id':c['id'], 'event_id':'provider-1', 'text':'Call +1 202-555-0142.'})
        timestamp = str(int(time.time()))
        signature = 'sha256='+hmac.new(self.secret.encode(), timestamp.encode()+b'.'+payload.encode(), hashlib.sha256).hexdigest()
        headers = {'X-SilverTrap-Timestamp':timestamp, 'X-SilverTrap-Signature':signature}
        self.assertEqual(self.request('/api/intake', 'POST', payload, headers, False)[0], 200)
        self.assertEqual(self.request('/api/intake', 'POST', payload, headers, False)[0], 200)
        self.assertEqual(len(self.service.get_case(c['id'])['messages']), 1)
        self.assertEqual(self.request('/api/intake', 'POST', payload, {**headers, 'X-SilverTrap-Signature':'bad'}, False)[0], 401)
        self.assertEqual(self.request('/api/intake', 'POST', payload, {**headers, 'X-SilverTrap-Timestamp':'1'}, False)[0], 401)

    def test_intake_disabled_by_default_and_never_delivers(self):
        self.service.config = replace(self.service.config, webhook_secret='')
        self.assertEqual(self.request('/api/intake', 'POST', '{}', authenticated=False)[0], 404)
        self.assertFalse(self.service.overview()['external_delivery'])

    def test_input_shape_and_request_size(self):
        self.assertEqual(self.request('/api/cases', 'POST', 'not-json')[0], 400)
        self.assertEqual(self.request('/api/cases', 'POST', '[]')[0], 400)
        self.assertEqual(self.request('/api/cases', 'POST', '{}', {'Content-Length':'262145'})[0], 413)

    def test_concurrent_steps_do_not_duplicate_evidence(self):
        c = self.service.create_case(scenario='tech-support')
        results = []
        threads = [threading.Thread(target=lambda: results.append(self.request(f"/api/cases/{c['id']}/simulate", 'POST', '{}')[0])) for _ in range(3)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(results, [200]*3)
        after = self.service.get_case(c['id'])
        self.assertEqual(after['cursor'], 3)
        self.assertEqual(len(after['messages']), 6)
        self.assertTrue(after['integrity']['valid'])


if __name__ == '__main__':
    unittest.main()
