"""A single small SQLite database, bounded writes, explicit transactions."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import threading


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


MESSAGE_FIELDS = ("id", "case_id", "sequence", "role", "text", "created_at", "raw_digest", "previous_hash")


def message_hash(message):
    return digest({key: message[key] for key in MESSAGE_FIELDS})


def verify_messages(messages, expected_count=None, expected_head=None):
    previous = "0" * 64
    for sequence, message in enumerate(messages, 1):
        if message["sequence"] != sequence or message["previous_hash"] != previous or message_hash(message) != message["evidence_hash"]:
            return False
        previous = message["evidence_hash"]
    return ((expected_count is None or expected_count == len(messages)) and
            (expected_head is None or expected_head == previous))


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
INSERT OR IGNORE INTO meta VALUES ('schema_version', '1');
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
INSERT OR IGNORE INTO settings VALUES ('stopped', 'false');
CREATE TABLE IF NOT EXISTS cases (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, persona_id TEXT NOT NULL,
 mode TEXT NOT NULL, status TEXT NOT NULL, scenario TEXT, cursor INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, model_calls INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS messages (
 id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id), sequence INTEGER NOT NULL,
 role TEXT NOT NULL CHECK(role IN ('inbound','persona')), text TEXT NOT NULL,
 created_at TEXT NOT NULL, raw_digest TEXT NOT NULL, previous_hash TEXT NOT NULL,
 evidence_hash TEXT NOT NULL, idempotency_key TEXT,
 UNIQUE(case_id,sequence), UNIQUE(case_id,idempotency_key));
CREATE TABLE IF NOT EXISTS findings (
 id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id),
 message_id TEXT NOT NULL REFERENCES messages(id), payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS indicators (
 id INTEGER PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id),
 message_id TEXT NOT NULL REFERENCES messages(id), kind TEXT NOT NULL,
 normalized TEXT NOT NULL, payload TEXT NOT NULL,
 UNIQUE(message_id,kind,normalized));
CREATE INDEX IF NOT EXISTS indicators_pivot ON indicators(kind,normalized,case_id);
CREATE INDEX IF NOT EXISTS messages_case ON messages(case_id,sequence);
CREATE INDEX IF NOT EXISTS findings_case ON findings(case_id);
CREATE TABLE IF NOT EXISTS drafts (
 id TEXT PRIMARY KEY, case_id TEXT NOT NULL REFERENCES cases(id),
 message_id TEXT NOT NULL REFERENCES messages(id), text TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS model_cache (case_id TEXT NOT NULL, fingerprint TEXT NOT NULL,
 payload TEXT NOT NULL, PRIMARY KEY(case_id,fingerprint));
CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, kind TEXT NOT NULL,
 payload TEXT NOT NULL, previous_hash TEXT NOT NULL, hash TEXT NOT NULL);
"""


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA busy_timeout=10000")
        self.db.executescript(SCHEMA)
        if self.db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0] != "1":
            raise RuntimeError("Unsupported database version; use the matching SilverTrap release.")
        try:
            self.path.chmod(0o600)
        except OSError:
            pass

    @contextmanager
    def transaction(self):
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                yield self.db
                self.db.execute("COMMIT")
            except BaseException:
                self.db.execute("ROLLBACK")
                raise

    @contextmanager
    def read(self):
        with self.lock:
            yield self.db

    def event(self, db, kind, payload):
        row = db.execute("SELECT hash FROM events ORDER BY id DESC LIMIT 1").fetchone()
        event = {"created_at": now(), "kind": kind, "payload": payload, "previous_hash": row[0] if row else "0"*64}
        db.execute("INSERT INTO events(created_at,kind,payload,previous_hash,hash) VALUES (?,?,?,?,?)",
                   (event["created_at"], kind, canonical(payload), event["previous_hash"], digest(event)))

    def backup(self, destination):
        destination = Path(destination).resolve()
        if destination == self.path.resolve():
            raise ValueError("Backup destination must differ from the working database.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with self.lock, sqlite3.connect(destination) as target:
            self.db.backup(target)
        try:
            destination.chmod(0o600)
        except OSError:
            pass
        return destination

    def close(self):
        with self.lock:
            self.db.close()
