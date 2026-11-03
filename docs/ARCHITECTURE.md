# Architecture

SilverTrap v0.1 implements the controlled-research half of a hybrid fraud-intelligence system. Its core product is a chronological reconstruction supported by exact evidence, not a transcript alone.

## Processing contracts

1. An authenticated operator, synthetic scenario, or explicitly configured signed intake submits text to an existing case.
2. The supervisor checks the emergency stop, case state, request size, case limits, and idempotency key.
3. Best-effort secret redaction runs before persistence. The unredacted text is discarded after fingerprinting.
4. A SQLite transaction appends the stored message to a hash chain, runs inbound-only analysts, and persists findings and normalized indicators.
5. Stage reconstruction distinguishes observed phrases, inferred categories/objectives, and missing evidence. Stages may overlap or repeat; there is no fabricated monotonic path.
6. The persona module selects a nonrepeating question using the most advanced observed stage in the latest evidence message. The persona's identity and earlier replies stay case-local.
7. The supervisor validates the locally authored template and queues it. New inbound evidence supersedes older pending drafts. A prompt-injection match pauses the case instead of creating a reply.
8. Simulation steps may commit a synthetic persona reply. A research approval records a local review only. There is no outbound transport to call.

All-step simulations use one transaction, so budget failures do not leave half an exchange. Manual imports likewise either commit the entire valid import or roll it back. Concurrent calls serialize at the database boundary. Reads are bounded by the case, message, and indicator limits.

## Analyst roles

| Role | Implementation | Output |
| --- | --- | --- |
| Persona | `personas.py` | Vetted stage-aware questions; three fictional profiles |
| Behavior | `intelligence.py` rules | Literal urgency, threat, secrecy, rapport, and authority evidence |
| Classifier | `intelligence.py` classifiers | Evidence-backed category hypotheses, including unclassified |
| Finance | `intelligence.py` reconstruction | Suspected objectives requiring explicit combinations of observed signals |
| Extraction | `intelligence.py` indicator parsers | Normalized candidates with exact message spans |
| Reconstruction | `intelligence.py` | Fixed stage reference, chronological event list, gaps and objectives |
| Supervisor | `safety.py`, `service.py` | Data minimization, state checks, limits, review and stop enforcement |

The deterministic rules are an inspectable baseline, not a learned classifier. Optional local model interpretation is a separate, manually requested second opinion. It cannot populate an observed stage merely by supplying a hypothesis. Literal quote validation verifies provenance, not the truth of the model's interpretation.

## Storage

| Table | Purpose |
| --- | --- |
| `cases` | Case mode, persona, lifecycle, scenario cursor and model attempts |
| `messages` | Isolated ordered records with role, redacted text, original digest and chained evidence hash |
| `findings` | Exact source offsets, quoted span, stage, type, epistemic status and engine origin |
| `indicators` | Indexed `(kind, normalized)` values and per-message occurrences |
| `drafts` | Pending, superseded, rejected, reviewed or simulated local persona drafts |
| `settings` | Persistent emergency stop |
| `model_cache` | Per-case model/input fingerprint and reserved/failed/discarded/complete attempt state |
| `events` | Append-only application audit events with a hash chain |
| `meta` | Schema version; unknown versions fail closed |

SQLite uses WAL, foreign keys, explicit transactions, indexed pivots, and a process lock. The supported v0.1 topology is one operator process per database. Multiple app replicas, shared network filesystems, and worker fleets are outside this version's operating model. Database page growth and WAL bytes count toward the write budget; a single transaction can exceed the budget slightly because the check is a high-water guard, not a filesystem quota.

## Evidence semantics

`observed` means a source phrase matched a transparent rule. It does not establish that a claim in that phrase is true. `inference` includes classifications, objectives, and local model hypotheses. Ownership, actor identity, unseen actions, and attribution stay unverified.

Spans use zero-based Unicode code points in stored redacted text. Evidence hashes bind message metadata, sequence, role, stored text, original digest, and the previous hash. JSON export additionally checksums the whole case and states the expected chain length and head. An independently retained export can detect later changes; an actor able to rewrite records and checksums can create a different internally consistent history. This is not a signed forensic acquisition or trusted timestamping service.

Indicators never trigger DNS lookups, HTTP visits, screenshots, wallet queries, or enrichment requests. Email local parts are lowercased as a pragmatic research normalization; URLs preserve path/query case and normalize the authority. US-format phone numbers normalize to `+1`. Wallet strings are syntax candidates, not checksum-validated or attributed addresses. Correlation counts distinct cases separately from per-message occurrences.

## Resource model

Message analysis is incremental; stored per-message findings are reused. The UI loads bounded case summaries and requests a full case on demand. SQLite substitutes for a separate task queue: simulation cursor, draft state, and model reservations survive restarts. There is no background retry loop, autonomous scheduler, or continuously running model.

Local model calls have one shared concurrency slot, a bounded recent context, a finite response read, and no automatic retry. Only a fixed local endpoint is reachable from that adapter. If the process exits after reserving an attempt, it remains reserved and consumes its budget; there is no ambiguous automatic replay. A future worker queue should use leases and explicit recovery rather than silently replaying side effects.
