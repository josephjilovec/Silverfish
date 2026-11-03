"""Orchestration: one pipeline, isolated cases, no outbound transport."""
import hashlib
import json
import re
import uuid

from .config import Config
from .intelligence import extract, reconstruct
from .personas import PERSONAS, draft
from .safety import alerts, redact, safe_draft
from .scenarios import BY_ID, SCENARIOS
from .store import Store, canonical, message_hash, now, verify_messages


class Problem(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def identifier(prefix):
    return prefix + "-" + uuid.uuid4().hex[:12]


class Service:
    def __init__(self, config: Config):
        self.config = config
        self.store = Store(config.data_dir / "silvertrap.sqlite3")

    def _case(self, db, case_id):
        if not isinstance(case_id, str) or len(case_id) > 40:
            raise Problem("Invalid case identifier")
        row = db.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
        if not row:
            raise Problem("Case not found", 404)
        return dict(row)

    def _stopped(self, db):
        return db.execute("SELECT value FROM settings WHERE key='stopped'").fetchone()[0] == "true"

    def _writable(self, db):
        if self._stopped(db):
            raise Problem("Network is paused by the emergency stop. Resume it in Controls.", 409)
        size = sum(p.stat().st_size for p in self.config.data_dir.glob("silvertrap.sqlite3*") if p.is_file())
        if size >= self.config.limits.max_database_bytes:
            raise Problem("Local database budget reached. Back up and archive before continuing.", 409)

    def _active(self, db, case_id):
        self._writable(db)
        case = self._case(db, case_id)
        if case["status"] != "active":
            raise Problem("Case is paused or closed", 409)
        return case

    def _new_case(self, db, title, persona_id, mode, scenario=None):
        self._writable(db)
        if db.execute("SELECT COUNT(*) FROM cases").fetchone()[0] >= self.config.limits.max_cases:
            raise Problem("Case limit reached", 409)
        if not isinstance(persona_id, str) or persona_id not in {p["id"] for p in PERSONAS}:
            raise Problem("Unknown persona")
        if not isinstance(title, str) or not 1 <= len(title.strip()) <= 120:
            raise Problem("Title must contain 1–120 characters")
        case_id, stamp = identifier("ST"), now()
        db.execute("INSERT INTO cases(id,title,persona_id,mode,status,scenario,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)",
                   (case_id, title.strip(), persona_id, mode, "active", scenario, stamp, stamp))
        self.store.event(db, "case.created", {"case_id": case_id, "mode": mode, "scenario": scenario})
        return case_id

    def create_case(self, title="Untitled investigation", persona_id="margaret", scenario=None):
        if scenario is not None and (not isinstance(scenario, str) or scenario not in BY_ID):
            raise Problem("Unknown scenario")
        if scenario:
            fixture = BY_ID[scenario]
            title, persona_id = fixture["title"], fixture["persona"]
        with self.store.transaction() as db:
            case_id = self._new_case(db, title, persona_id, "simulation" if scenario else "research", scenario)
        return self.get_case(case_id)

    def _messages(self, db, case_id):
        return [dict(row) for row in db.execute("SELECT * FROM messages WHERE case_id=? ORDER BY sequence", (case_id,))]

    def _findings(self, db, case_id):
        return [json.loads(row[0]) for row in db.execute("SELECT payload FROM findings WHERE case_id=? ORDER BY rowid", (case_id,))]

    def _record(self, db, case, role, text, key=None):
        if not isinstance(text, str) or not text.strip():
            raise Problem("Message text is required")
        text = text.strip()
        raw = text.encode()
        if len(raw) > self.config.limits.max_message_bytes:
            raise Problem("Message exceeds 8 KiB", 413)
        messages = self._messages(db, case["id"])
        if len(messages) >= self.config.limits.max_messages:
            raise Problem("Conversation turn limit reached", 409)
        clean = redact(text)
        if sum(len(m["text"].encode()) for m in messages) + len(clean.encode()) > self.config.limits.max_case_bytes:
            raise Problem("Conversation storage budget reached", 409)
        stamp = now()
        message = {"id": identifier("MSG"), "case_id": case["id"], "sequence": len(messages)+1,
                   "role": role, "text": clean, "created_at": stamp,
                   "raw_digest": hashlib.sha256(raw).hexdigest(),
                   "previous_hash": messages[-1]["evidence_hash"] if messages else "0"*64}
        message["evidence_hash"] = message_hash(message)
        db.execute("INSERT INTO messages VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (message["id"], case["id"], message["sequence"], role, clean, stamp,
                    message["raw_digest"], message["previous_hash"], message["evidence_hash"], key))
        message["first_inbound"] = role == "inbound" and not any(m["role"] == "inbound" for m in messages)
        findings, indicators = extract(message)
        for finding in findings:
            db.execute("INSERT OR IGNORE INTO findings VALUES (?,?,?,?)", (finding["id"], case["id"], message["id"], canonical(finding)))
        for indicator in indicators:
            db.execute("INSERT OR IGNORE INTO indicators(case_id,message_id,kind,normalized,payload) VALUES (?,?,?,?,?)",
                       (case["id"], message["id"], indicator["kind"], indicator["normalized"], canonical(indicator)))
        db.execute("UPDATE cases SET updated_at=? WHERE id=?", (stamp, case["id"]))
        self.store.event(db, "message.recorded", {"case_id": case["id"], "message_id": message["id"], "evidence_hash": message["evidence_hash"], "redacted": clean != text})
        return message

    def _queue(self, db, case, message):
        db.execute("UPDATE drafts SET status='superseded' WHERE case_id=? AND status='pending'", (case["id"],))
        if "prompt_injection" in alerts(message["text"]):
            db.execute("UPDATE cases SET status='paused' WHERE id=?", (case["id"],))
            self.store.event(db, "safety.paused", {"case_id": case["id"], "reason": "prompt_injection"})
            return
        messages = self._messages(db, case["id"])
        report = reconstruct(messages, self._findings(db, case["id"]), case["status"])
        reply = draft(case["persona_id"], report, messages)
        if reply and safe_draft(reply):
            db.execute("INSERT INTO drafts VALUES (?,?,?,?,?,?)",
                       (identifier("DR"), case["id"], message["id"], reply, "pending", now()))

    def ingest(self, case_id, text, idempotency_key=None):
        if idempotency_key is not None and (not isinstance(idempotency_key, str) or not re.fullmatch(r"[\w.:-]{1,100}", idempotency_key)):
            raise Problem("Invalid idempotency key")
        with self.store.transaction() as db:
            case = self._case(db, case_id)
            existing = db.execute("SELECT raw_digest FROM messages WHERE case_id=? AND idempotency_key=?", (case_id, idempotency_key)).fetchone() if idempotency_key else None
            if existing:
                if not isinstance(text, str) or existing[0] != hashlib.sha256(text.strip().encode()).hexdigest():
                    raise Problem("Idempotency key was already used for different content", 409)
            else:
                self._active(db, case_id)
                message = self._record(db, case, "inbound", text, idempotency_key)
                self._queue(db, case, message)
        return self.get_case(case_id)

    def decide_draft(self, case_id, draft_id, decision):
        if not isinstance(decision, str) or decision not in {"approve", "reject"}:
            raise Problem("Decision must be approve or reject")
        with self.store.transaction() as db:
            case = self._active(db, case_id)
            row = db.execute("SELECT * FROM drafts WHERE id=? AND case_id=?", (draft_id, case_id)).fetchone()
            if not row:
                raise Problem("Draft not found", 404)
            if row["status"] != "pending":
                raise Problem("This draft has already been decided or superseded", 409)
            if decision == "approve":
                if not safe_draft(row["text"]):
                    raise Problem("Supervisor blocked draft", 409)
                if case["mode"] == "simulation":
                    self._record(db, case, "persona", row["text"])
                outcome = "simulated" if case["mode"] == "simulation" else "reviewed"
            else:
                outcome = "rejected"
            db.execute("UPDATE drafts SET status=? WHERE id=?", (outcome, draft_id))
            self.store.event(db, "draft." + outcome, {"case_id": case_id, "draft_id": draft_id, "external_delivery": False})
        return self.get_case(case_id)

    def simulate(self, case_id, all_steps=False):
        # A single transaction serializes concurrent step calls and makes all-step runs atomic.
        with self.store.transaction() as db:
            case = self._active(db, case_id)
            if case["mode"] != "simulation" or case["scenario"] not in BY_ID:
                raise Problem("This case is not a simulation", 409)
            fixture = BY_ID[case["scenario"]]
            count = len(fixture["messages"]) - case["cursor"] if all_steps else 1
            if case["cursor"] >= len(fixture["messages"]):
                raise Problem("Scenario is complete", 409)
            for _ in range(count):
                case = self._active(db, case_id)
                if case["cursor"] >= len(fixture["messages"]):
                    break
                message = self._record(db, case, "inbound", fixture["messages"][case["cursor"]], f"sim:{case['cursor']}")
                self._queue(db, case, message)
                db.execute("UPDATE cases SET cursor=cursor+1 WHERE id=?", (case_id,))
                pending = db.execute("SELECT * FROM drafts WHERE case_id=? AND status='pending'", (case_id,)).fetchone()
                if pending:
                    self._record(db, case, "persona", pending["text"])
                    db.execute("UPDATE drafts SET status='simulated' WHERE id=?", (pending["id"],))
                if self._case(db, case_id)["status"] != "active":
                    break
            self.store.event(db, "simulation.advanced", {"case_id": case_id})
        return self.get_case(case_id)

    def import_transcript(self, title, messages, persona_id="margaret"):
        if not isinstance(messages, list) or not 1 <= len(messages) <= self.config.limits.max_messages:
            raise Problem("Import must contain 1–80 messages")
        for item in messages:
            if not isinstance(item, dict) or item.get("role") not in {"inbound", "persona"}:
                raise Problem("Each message needs a role of inbound or persona")
        with self.store.transaction() as db:
            case_id = self._new_case(db, title, persona_id, "transcript")
            case = self._case(db, case_id)
            for item in messages:
                self._record(db, case, item["role"], item.get("text"))
            db.execute("UPDATE cases SET status='paused' WHERE id=?", (case_id,))
        return self.get_case(case_id)

    def set_status(self, case_id, status):
        if not isinstance(status, str) or status not in {"active", "paused", "closed"}:
            raise Problem("Unknown case status")
        with self.store.transaction() as db:
            case = self._case(db, case_id)
            if case["status"] == "closed" and status != "closed":
                raise Problem("Closed cases are read-only. Start a new case to continue research.", 409)
            if status == "active":
                self._writable(db)
                if case["mode"] == "transcript":
                    raise Problem("Imported transcripts remain read-only", 409)
            db.execute("UPDATE cases SET status=?,updated_at=? WHERE id=?", (status, now(), case_id))
            if status != "active":
                db.execute("UPDATE drafts SET status='superseded' WHERE case_id=? AND status='pending'", (case_id,))
            self.store.event(db, "case.status", {"case_id": case_id, "status": status})
        return self.get_case(case_id)

    def set_stop(self, stopped):
        if type(stopped) is not bool:
            raise Problem("stopped must be true or false")
        with self.store.transaction() as db:
            db.execute("UPDATE settings SET value=? WHERE key='stopped'", (canonical(stopped),))
            if stopped:
                db.execute("UPDATE drafts SET status='superseded' WHERE status='pending'")
            self.store.event(db, "network.stopped" if stopped else "network.resumed", {})
        return self.overview()

    def get_case(self, case_id):
        with self.store.read() as db:
            case = self._case(db, case_id)
            messages = self._messages(db, case_id)
            findings = self._findings(db, case_id)
            case.update(messages=messages, findings=findings,
                        indicators=[json.loads(r[0]) for r in db.execute("SELECT payload FROM indicators WHERE case_id=? ORDER BY id", (case_id,))],
                        drafts=[dict(r) for r in db.execute("SELECT * FROM drafts WHERE case_id=? ORDER BY created_at DESC", (case_id,))],
                        analysis=reconstruct(messages, findings, case["status"]),
                        integrity={"valid": verify_messages(messages), "message_count": len(messages), "head": messages[-1]["evidence_hash"] if messages else "0"*64},
                        safety_alerts=sorted({a for m in messages if m["role"] == "inbound" for a in alerts(m["text"])}),
                        limits={"messages": self.config.limits.max_messages, "model_calls": self.config.limits.max_model_calls},
                        scenario_total=len(BY_ID[case["scenario"]]["messages"]) if case["scenario"] in BY_ID else 0)
            return case

    def list_cases(self):
        with self.store.read() as db:
            cases = [dict(r) for r in db.execute("SELECT c.*, (SELECT COUNT(*) FROM messages m WHERE m.case_id=c.id) AS message_count, (SELECT COUNT(*) FROM indicators i WHERE i.case_id=c.id) AS indicator_count FROM cases c ORDER BY created_at DESC LIMIT ?", (self.config.limits.max_cases,))]
            for case in cases:
                fs = self._findings(db, case["id"])
                classifications = [f["label"] for f in fs if f["kind"] == "classification"]
                case["classification"] = max(dict.fromkeys(classifications), key=classifications.count) if classifications else "Unclassified interaction"
                case["coverage"] = len({f["stage"] for f in fs if f["kind"] != "classification" and f["stage"] != "exit" and f["basis"] == "observed"})
            return cases

    def overview(self):
        with self.store.read() as db:
            return {"version": "0.1.0", "mode": "Simulation & controlled research", "stopped": self._stopped(db),
                    "cases": db.execute("SELECT COUNT(*) FROM cases").fetchone()[0],
                    "active": db.execute("SELECT COUNT(*) FROM cases WHERE status='active'").fetchone()[0],
                    "messages": db.execute("SELECT COUNT(*) FROM messages").fetchone()[0],
                    "indicators": db.execute("SELECT COUNT(*) FROM (SELECT DISTINCT kind,normalized FROM indicators)").fetchone()[0],
                    "pending": db.execute("SELECT COUNT(*) FROM drafts WHERE status='pending'").fetchone()[0],
                    "model_calls": db.execute("SELECT COALESCE(SUM(model_calls),0) FROM cases").fetchone()[0],
                    "model": self.config.ollama_model or None, "external_delivery": False,
                    "webhook_enabled": bool(self.config.webhook_secret),
                    "personas": PERSONAS,
                    "scenarios": [{k:v for k,v in s.items() if k != "messages"} for s in SCENARIOS],
                    "limits": self.config.limits.__dict__}

    def indicator_index(self):
        with self.store.read() as db:
            rows = db.execute("SELECT kind,normalized,COUNT(DISTINCT case_id) AS case_count,COUNT(*) AS occurrences FROM indicators GROUP BY kind,normalized ORDER BY case_count DESC,occurrences DESC LIMIT 1000")
            items = []
            for row in rows:
                item = dict(row)
                item["cases"] = [dict(r) for r in db.execute("SELECT DISTINCT c.id,c.title FROM cases c JOIN indicators i ON c.id=i.case_id WHERE i.kind=? AND i.normalized=? ORDER BY c.created_at", (row["kind"], row["normalized"]))]
                items.append(item)
            return {"items": items, "caveat": "Shared indicators are investigative leads, not proof of common ownership or a criminal network."}

    def events(self):
        with self.store.read() as db:
            return [dict(r) for r in db.execute("SELECT * FROM events ORDER BY id DESC LIMIT 100")]

    def seed(self):
        if not self.list_cases():
            for scenario in ("tech-support", "social-security", "investment"):
                case = self.create_case(scenario=scenario)
                self.simulate(case["id"], all_steps=True)
