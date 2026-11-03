"""Authenticated local command center and an opt-in, intake-only signed webhook."""
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import threading
import time
from urllib.parse import urlsplit

from .model import LocalAnalyst
from .reports import bundle, markdown
from .service import Problem
from .store import canonical

WEB = Path(__file__).parent / "web"
STATIC = {"/": "index.html", "/app.js": "app.js", "/styles.css": "styles.css", "/mark.svg": "mark.svg"}


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, service):
        if len(service.config.operator_token) < 32:
            raise ValueError("Operator token must be at least 32 characters")
        self.service = service
        self.analyst = LocalAnalyst(service)
        self.slots = threading.BoundedSemaphore(16)
        super().__init__(address, Handler)

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False):
            request.sendall(b"HTTP/1.1 503 Service Unavailable\r\nConnection: close\r\nContent-Length: 0\r\n\r\n")
            self.shutdown_request(request)
            return
        try:
            request.settimeout(10)
            super().process_request(request, address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.slots.release()


class Handler(BaseHTTPRequestHandler):
    server_version = "SilverTrap/0.1"

    def log_message(self, fmt, *args):
        # Query strings, source text, and bearer tokens never enter request logs.
        return

    def _respond(self, status, body, content_type="application/json; charset=utf-8", filename=None):
        if not isinstance(body, bytes):
            body = canonical(body).encode() if content_type.startswith("application/json") else body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; font-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(body)

    def _authorize(self):
        origin = self.headers.get("Origin")
        if origin and urlsplit(origin).netloc != self.headers.get("Host", ""):
            raise Problem("Cross-origin API access is disabled", 403)
        actual = self.headers.get("Authorization", "")
        expected = "Bearer " + self.server.service.config.operator_token
        if not hmac.compare_digest(actual.encode(), expected.encode()):
            raise Problem("Enter the operator access code printed by the local server", 401)

    def _body(self):
        if self.headers.get("Transfer-Encoding"):
            raise Problem("Chunked request bodies are not supported", 400)
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise Problem("Invalid Content-Length") from None
        if not 0 < length <= self.server.service.config.limits.max_request_bytes:
            raise Problem("Request exceeds the size budget or has no body", 413)
        if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
            raise Problem("Use application/json", 415)
        raw = self.rfile.read(length)
        if len(raw) != length:
            raise Problem("Incomplete request body")
        try:
            data = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            raise Problem("Invalid JSON") from None
        if not isinstance(data, dict):
            raise Problem("JSON body must be an object")
        return data, raw

    def _route(self):
        path = urlsplit(self.path).path
        parts = path.strip("/").split("/")
        service = self.server.service
        if self.command == "GET" and path in STATIC:
            file = WEB / STATIC[path]
            return self._respond(200, file.read_bytes(), mimetypes.guess_type(file.name)[0] or "text/plain")
        if self.command == "POST" and path == "/api/intake":
            secret = service.config.webhook_secret
            if not secret:
                raise Problem("Signed intake is disabled", 404)
            data, raw = self._body()
            timestamp = self.headers.get("X-SilverTrap-Timestamp", "")
            try:
                if abs(time.time() - int(timestamp)) > 300:
                    raise ValueError()
            except ValueError:
                raise Problem("Intake signature timestamp expired or invalid", 401) from None
            signature = "sha256=" + hmac.new(secret.encode(), timestamp.encode()+b"."+raw, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature.encode(), self.headers.get("X-SilverTrap-Signature", "").encode()):
                raise Problem("Invalid intake signature", 401)
            if not isinstance(data.get("event_id"), str) or not data["event_id"]:
                raise Problem("event_id is required for replay protection")
            case = service.get_case(data.get("case_id", ""))
            if case["mode"] != "research":
                raise Problem("Intake requires a controlled research case", 409)
            result = service.ingest(case["id"], data.get("text"), "intake:"+data["event_id"])
            return self._respond(200, {"case_id": result["id"], "accepted": True, "external_delivery": False})
        self._authorize()
        if self.command == "GET":
            if path == "/api/overview":
                return self._respond(200, service.overview())
            if path == "/api/cases":
                return self._respond(200, {"items": service.list_cases()})
            if path == "/api/indicators":
                return self._respond(200, service.indicator_index())
            if path == "/api/events":
                return self._respond(200, {"items": service.events()})
            if len(parts) in {3, 4} and parts[:2] == ["api", "cases"]:
                case = service.get_case(parts[2])
                if len(parts) == 3:
                    return self._respond(200, case)
                if parts[3] == "export.json":
                    return self._respond(200, bundle(case), filename=case["id"]+".json")
                if parts[3] == "report.md":
                    return self._respond(200, markdown(case), "text/markdown; charset=utf-8", case["id"]+".md")
        if self.command == "POST":
            data, _ = self._body()
            if path == "/api/cases":
                return self._respond(201, service.create_case(data.get("title", "Untitled investigation"), data.get("persona_id", "margaret"), data.get("scenario")))
            if path == "/api/import":
                return self._respond(201, service.import_transcript(data.get("title", "Imported transcript"), data.get("messages"), data.get("persona_id", "margaret")))
            if path == "/api/controls":
                return self._respond(200, service.set_stop(data.get("stopped")))
            if len(parts) >= 4 and parts[:2] == ["api", "cases"]:
                case_id, action = parts[2:4]
                if len(parts) == 4:
                    if action == "messages":
                        return self._respond(200, service.ingest(case_id, data.get("text"), data.get("idempotency_key")))
                    if action == "simulate":
                        return self._respond(200, service.simulate(case_id, data.get("all_steps") is True))
                    if action == "status":
                        return self._respond(200, service.set_status(case_id, data.get("status")))
                    if action == "analyze":
                        return self._respond(200, self.server.analyst.analyze(case_id))
                if len(parts) == 5 and action == "drafts":
                    return self._respond(200, service.decide_draft(case_id, parts[4], data.get("decision")))
        raise Problem("Endpoint not found", 404)

    def _handle(self):
        try:
            self._route()
        except Problem as error:
            self._respond(error.status, {"error": str(error)})
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            pass
        except Exception:
            self._respond(500, {"error": "Internal error. The request was not completed."})

    do_GET = _handle
    do_POST = _handle
