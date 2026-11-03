from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest

from silvertrap.config import Config, Limits
from silvertrap.intelligence import extract
from silvertrap.model import LocalAnalyst, validate_hypotheses
from silvertrap.reports import bundle, markdown, verify_bundle
from silvertrap.safety import safe_draft
from silvertrap.scenarios import SCENARIOS
from silvertrap.service import Problem, Service


class BaseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.config = Config(Path(self.tmp.name), operator_token='test-operator-' + 'x'*32)
        self.service = Service(self.config)

    def tearDown(self):
        self.service.store.close()
        self.tmp.cleanup()


class ServiceTest(BaseTest):
    def test_scenarios_classify_and_cite_literal_evidence(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario['id']):
                c = self.service.create_case(scenario=scenario['id'])
                c = self.service.simulate(c['id'], True)
                self.assertEqual(c['analysis']['classification'], scenario['category'])
                self.assertTrue(c['integrity']['valid'])
                self.assertEqual(c['analysis']['quality']['findings'], c['analysis']['quality']['evidence_linked'])
                self.assertTrue(verify_bundle(bundle(c)))
                messages = {m['id']:m for m in c['messages']}
                for f in c['findings']:
                    self.assertEqual(messages[f['message_id']]['role'], 'inbound')
                    self.assertEqual(messages[f['message_id']]['text'][f['start']:f['end']], f['quote'])
                if scenario['id'] == 'benign':
                    self.assertFalse(c['analysis']['objectives'])
                if scenario['id'] == 'injection':
                    self.assertEqual(c['status'], 'paused')
                    self.assertFalse(c['drafts'])

    def test_reconstruction_marks_gaps_instead_of_inventing_them(self):
        c = self.service.create_case()
        c = self.service.ingest(c['id'], 'Your library book is ready.')
        self.assertEqual(c['analysis']['coverage']['observed'], 1)
        self.assertFalse(c['analysis']['objectives'])
        self.assertFalse(next(s for s in c['analysis']['stages'] if s['id']=='theft')['observed'])

    def test_persona_text_never_becomes_adversary_intelligence(self):
        c = self.service.import_transcript('Role isolation', [
            {'role':'persona', 'text':'My fictional notes mention bitcoin and https://persona.invalid/'},
            {'role':'inbound', 'text':'The book is ready.'}])
        self.assertFalse(c['indicators'])
        self.assertEqual([f['kind'] for f in c['findings']], ['contact'])

    def test_case_memory_and_drafts_are_isolated(self):
        a, b = self.service.create_case(title='A'), self.service.create_case(title='B')
        a = self.service.ingest(a['id'], 'Private marker alpha. This is Microsoft support.')
        b = self.service.ingest(b['id'], 'Unrelated marker beta.')
        self.assertNotIn('alpha', str(b))
        with self.assertRaises(Problem):
            self.service.decide_draft(b['id'], a['drafts'][0]['id'], 'approve')

    def test_idempotency_is_payload_bound(self):
        c = self.service.create_case()
        first = self.service.ingest(c['id'], 'Same source message.', 'event-1')
        second = self.service.ingest(c['id'], 'Same source message.', 'event-1')
        self.assertEqual(first['messages'], second['messages'])
        self.assertEqual(len(second['drafts']), 1)
        with self.assertRaises(Problem):
            self.service.ingest(c['id'], 'Changed message.', 'event-1')
        self.service.ingest(c['id'], 'My password is first-secret', 'secret-event')
        with self.assertRaises(Problem):
            self.service.ingest(c['id'], 'My password is different-secret', 'secret-event')

    def test_new_source_supersedes_old_draft_and_review_never_delivers(self):
        c = self.service.create_case()
        a = self.service.ingest(c['id'], 'Hello.')
        old = a['drafts'][0]['id']
        b = self.service.ingest(c['id'], 'What is your full name?')
        with self.assertRaises(Problem):
            self.service.decide_draft(c['id'], old, 'approve')
        pending = next(d for d in b['drafts'] if d['status']=='pending')
        c = self.service.decide_draft(c['id'], pending['id'], 'approve')
        self.assertEqual(len(c['messages']), 2)
        self.assertIn('reviewed', [d['status'] for d in c['drafts']])
        self.assertFalse(self.service.overview()['external_delivery'])
        with self.assertRaises(Problem):
            self.service.decide_draft(c['id'], pending['id'], 'approve')

    def test_emergency_stop_survives_restart_and_invalidates_pending(self):
        c = self.service.create_case()
        c = self.service.ingest(c['id'], 'Hello.')
        pending = c['drafts'][0]['id']
        self.service.set_stop(True)
        self.service.store.close()
        self.service = Service(self.config)
        self.assertTrue(self.service.overview()['stopped'])
        with self.assertRaises(Problem):
            self.service.ingest(c['id'], 'Another message.')
        with self.assertRaises(Problem):
            self.service.create_case()
        self.service.set_stop(False)
        with self.assertRaises(Problem):
            self.service.decide_draft(c['id'], pending, 'approve')

    def test_limits_fail_atomically(self):
        self.service.config = replace(self.config, limits=Limits(max_messages=1))
        c = self.service.create_case(scenario='tech-support')
        with self.assertRaises(Problem):
            self.service.simulate(c['id'])  # needs both inbound and persona turns
        self.assertFalse(self.service.get_case(c['id'])['messages'])
        self.service.ingest(c['id'], 'First message.')
        with self.assertRaises(Problem):
            self.service.ingest(c['id'], 'Second message.')
        self.assertEqual(len(self.service.get_case(c['id'])['messages']), 1)

    def test_oversized_input_and_invalid_import_leave_no_partial_case(self):
        c = self.service.create_case()
        with self.assertRaises(Problem):
            self.service.ingest(c['id'], 'z'*8193)
        count = self.service.overview()['cases']
        with self.assertRaises(Problem):
            self.service.import_transcript('Broken import', [{'role':'inbound','text':'ok'}, {'role':'inbound','text':''}])
        self.assertEqual(self.service.overview()['cases'], count)

    def test_closed_and_imported_cases_are_read_only(self):
        c = self.service.create_case()
        self.service.set_status(c['id'], 'closed')
        with self.assertRaises(Problem):
            self.service.set_status(c['id'], 'active')
        with self.assertRaises(Problem):
            self.service.ingest(c['id'], 'Cannot add this.')
        imported = self.service.import_transcript('Imported', [{'role':'inbound','text':'Source.'}])
        with self.assertRaises(Problem):
            self.service.set_status(imported['id'], 'active')

    def test_redaction_happens_before_storage_and_analysis(self):
        c = self.service.create_case()
        c = self.service.ingest(c['id'], 'My password is p@ss-secret. SSN 123-45-6789. Card 4111 1111 1111 1111.')
        text = c['messages'][0]['text']
        for secret in ('p@ss-secret', '123-45-6789', '4111 1111 1111 1111'):
            self.assertNotIn(secret, text)
        self.assertTrue(c['integrity']['valid'])
        self.assertFalse(safe_draft('My password is real-secret'))

    def test_cross_case_correlation_deduplicates_within_case(self):
        for title in ['One', 'Two']:
            c = self.service.create_case(title=title)
            self.service.ingest(c['id'], 'Call +1 202-555-0142.')
            self.service.ingest(c['id'], 'Call 202-555-0142 again.')
        phone = next(i for i in self.service.indicator_index()['items'] if i['kind']=='phone')
        self.assertEqual((phone['case_count'], phone['occurrences']), (2, 4))

    def test_urls_preserve_path_case_and_evidence_offsets(self):
        c = self.service.create_case()
        c = self.service.ingest(c['id'], '📬 Go to HTTPS://Support.INVALID/Case/ABC?Ref=X. Email A@B.invalid.')
        url = next(i for i in c['indicators'] if i['kind']=='url')
        self.assertEqual(url['normalized'], 'https://support.invalid/Case/ABC?Ref=X')
        for i in c['indicators']:
            self.assertEqual(c['messages'][0]['text'][i['start']:i['end']], i['value'])

    def test_negated_sensitive_instruction_is_not_an_action_request(self):
        message = {'id':'m', 'sequence':1, 'role':'inbound', 'text':"Never share your password. Don't install this program."}
        findings, _ = extract(message)
        self.assertNotIn('credential_request', [f['kind'] for f in findings])
        self.assertNotIn('remote_access', [f['kind'] for f in findings])

    def test_export_detects_modified_deleted_and_reordered_messages(self):
        c = self.service.create_case(scenario='tech-support')
        c = self.service.simulate(c['id'], True)
        original = bundle(c)
        self.assertTrue(verify_bundle(original))
        for operation in ['modify','delete','reorder']:
            changed = deepcopy(original)
            if operation == 'modify': changed['case']['messages'][0]['text'] += 'tampered'
            if operation == 'delete': changed['case']['messages'].pop()
            if operation == 'reorder': changed['case']['messages'].reverse()
            self.assertFalse(verify_bundle(changed))
        self.assertIn('hxxps', markdown(c))

    def test_sqlite_backup_captures_committed_wal_data(self):
        c = self.service.create_case()
        self.service.ingest(c['id'], 'Evidence to preserve.')
        destination = self.service.store.backup(Path(self.tmp.name)/'backup.sqlite3')
        with sqlite3.connect(destination) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM messages').fetchone()[0], 1)


class ModelTest(BaseTest):
    def test_model_disabled_without_configuration(self):
        c = self.service.create_case()
        with self.assertRaises(Problem):
            LocalAnalyst(self.service).analyze(c['id'])
        self.assertEqual(self.service.get_case(c['id'])['model_calls'], 0)

    def test_model_requires_literal_inbound_evidence(self):
        messages = [{'id':'a','role':'inbound','text':'Act now.'}, {'id':'b','role':'persona','text':'Hello.'}]
        for message_id, quote in [('a', 'Invented quote'), ('b', 'Hello.'), ('missing', 'Act now.')]:
            with self.assertRaises(ValueError):
                validate_hypotheses({'hypotheses':[{'message_id':message_id,'quote':quote,'stage':'trust','label':'Hypothesis'}]}, messages)

    def test_model_cache_budget_and_hypothesis_not_counted_as_observation(self):
        self.service.config = replace(self.config, ollama_model='test-local', limits=Limits(max_model_calls=1))
        c = self.service.create_case()
        c = self.service.ingest(c['id'], 'Hello there.')
        calls = []
        def transport(model, messages):
            calls.append(messages)
            return {'hypotheses':[{'message_id':messages[-1]['id'], 'quote':'Hello', 'stage':'theft', 'label':'An unsupported possibility requiring review'}]}
        analyst = LocalAnalyst(self.service, transport)
        first = analyst.analyze(c['id'])
        second = analyst.analyze(c['id'])
        self.assertTrue(second['cached'])
        self.assertEqual(len(calls), 1)
        self.assertEqual(first['case']['analysis']['coverage']['observed'], 1)
        self.service.ingest(c['id'], 'New evidence.')
        with self.assertRaises(Problem):
            analyst.analyze(c['id'])

    def test_model_hallucination_fails_without_rewriting_evidence(self):
        self.service.config = replace(self.config, ollama_model='test-local')
        c = self.service.ingest(self.service.create_case()['id'], 'Actual evidence.')
        analyst = LocalAnalyst(self.service, lambda *_: {'hypotheses':[{'message_id':c['messages'][0]['id'], 'quote':'Invented event', 'stage':'theft', 'label':'No'}]})
        with self.assertRaises(Problem): analyst.analyze(c['id'])
        after = self.service.get_case(c['id'])
        self.assertEqual(c['messages'], after['messages'])
        self.assertEqual(after['model_calls'], 1)

    def test_stop_during_model_call_discards_result(self):
        self.service.config = replace(self.config, ollama_model='test-local')
        c = self.service.ingest(self.service.create_case()['id'], 'Actual evidence.')
        def transport(*_):
            self.service.set_stop(True)
            return {'hypotheses':[]}
        with self.assertRaises(Problem):
            LocalAnalyst(self.service, transport).analyze(c['id'])
        self.assertTrue(self.service.overview()['stopped'])


if __name__ == '__main__':
    unittest.main()
