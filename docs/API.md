# API

All operator API routes require `Authorization: Bearer <operator-access-code>`. The local server generates a random code on first start unless `SILVERTRAP_OPERATOR_TOKEN` supplies at least 32 characters. The dashboard holds the code in tab memory, not local storage. Responses use `Cache-Control: no-store`; cross-origin operator access is rejected.

Send JSON bodies with `Content-Type: application/json`. Maximum body size is 256 KiB; messages are limited separately to 8 KiB. Errors return `{"error":"description"}` with a relevant 4xx or 5xx status.

| Method | Route | Purpose / JSON body |
| --- | --- | --- |
| GET | `/api/overview` | Counts, configuration, limits, personas, scenario metadata |
| GET | `/api/cases` | Bounded case summaries |
| POST | `/api/cases` | `{ "scenario": "tech-support" }` or `{ "title": "Research", "persona_id": "arthur" }` |
| GET | `/api/cases/{id}` | Full case, evidence, reconstruction and integrity result |
| POST | `/api/cases/{id}/messages` | `{ "text": "…", "idempotency_key": "provider-event-id" }` |
| POST | `/api/cases/{id}/simulate` | `{ "all_steps": true }`; omit/false for one exchange |
| POST | `/api/cases/{id}/status` | `{ "status": "active" }`, `paused`, or `closed` |
| POST | `/api/cases/{id}/drafts/{draft_id}` | `{ "decision": "approve" }` or `reject`; no external delivery |
| POST | `/api/cases/{id}/analyze` | `{}`; explicitly configured local model only |
| GET | `/api/cases/{id}/export.json` | Portable evidence bundle with checksums |
| GET | `/api/cases/{id}/report.md` | Markdown case reconstruction |
| POST | `/api/import` | `{ "title": "Transcript", "messages": [{ "role": "inbound", "text": "…" }] }` |
| GET | `/api/indicators` | Normalized indicator index and distinct case pivots |
| GET | `/api/events` | Latest 100 audit events |
| POST | `/api/controls` | `{ "stopped": true }` or false |

Repeated idempotency keys return the existing case only if the original trimmed message fingerprint matches. A reused key with different content returns 409, including changes that redaction would hide. Closing a case prevents reopening it; imported transcripts cannot be activated. Emergency stop does not erase records or automatically resume individual paused cases.

## Signed inbound integration seam

`POST /api/intake` is disabled unless `SILVERTRAP_WEBHOOK_SECRET` is configured. Use a distinct high-entropy secret, at least 32 random characters. This is an adapter contract, not a connection to an email or telephony service. The secret is separate from the operator code. Create a manual research case first; simulation and transcript cases reject adapter intake.

Payload:

```json
{"case_id":"ST-existing-case-id","event_id":"provider-message-id","text":"Inbound source text"}
```

Headers:

- `Content-Type: application/json`
- `X-SilverTrap-Timestamp: <Unix timestamp in seconds>`
- `X-SilverTrap-Signature: sha256=<hex HMAC-SHA256>`

Compute HMAC over the exact bytes `timestamp + "." + raw_request_body` using the dedicated secret. The signed timestamp must be within five minutes of the server clock. Event IDs are mandatory and must fit the per-case idempotency-key limit after the `intake:` prefix. Event IDs can use letters, digits, underscores, dots, colons, and hyphens. Retried signatures may use a fresh timestamp with the same body and event ID. Intake never returns a send instruction or persona draft.

Python adapter signing example (the adapter is responsible for obtaining a message from an approved dedicated channel):

```python
import hashlib, hmac, json, os, time, urllib.request

payload = {"case_id": "ST-your-case", "event_id": "provider-unique-id", "text": "Source text"}
raw = json.dumps(payload, separators=(",", ":")).encode()
timestamp = str(int(time.time()))
signature = hmac.new(os.environ["SILVERTRAP_WEBHOOK_SECRET"].encode(),
                     timestamp.encode() + b"." + raw, hashlib.sha256).hexdigest()
request = urllib.request.Request("http://127.0.0.1:8787/api/intake", raw, headers={
    "Content-Type": "application/json",
    "X-SilverTrap-Timestamp": timestamp,
    "X-SilverTrap-Signature": "sha256=" + signature,
})
with urllib.request.urlopen(request, timeout=10) as response:
    print(response.status)
```

To expose intake beyond loopback, first add a properly configured TLS reverse proxy, upstream identity/rate controls, dedicated channel routing, and monitoring. Do not expose this prototype's plain HTTP operator surface directly to the internet. Attachment handling is absent: send text only, never attachment bytes or download instructions.
