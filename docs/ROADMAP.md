# Evaluation and next milestones

## Delivered in v0.1

An authenticated command center; isolated persistent cases; three synthetic personas; seven analyst roles; nine scenarios; incremental evidence-linked extraction; chronology and stage/gap reconstruction; suspected financial objectives; indicator correlation; draft review; controls and budgets; optional local-model second opinion; signed intake contract; evidence exports; backups; Windows launcher; Docker packaging; offline tests and CI.

The application does not claim a calibrated confidence percentage or independently measured detection accuracy. The UI reports observed stage coverage, unique indicators, source-quote linkage, and operational counts. Conversation time is not presented as prevented victimization or recovered money.

## Validation measures

| Measure | Current measurement | Next meaningful validation |
| --- | --- | --- |
| Stage recognition | Transparent rule matches on synthetic fixtures | Blind stage annotations by at least two reviewers; precision/recall per stage |
| Attack-chain reconstruction | Exact provenance and preserved chronological ordering | Reviewer agreement on sequence, repeated phases and evidence gaps |
| Indicators | Normalized candidates, occurrences and distinct cases | Precision/recall on obfuscated and multilingual held-out messages |
| Financial objectives | Evidence-linked rule-based hypotheses | Independent labeling of intent and mechanisms; ambiguity/error review |
| Evidence support | Literal quote/offset validation | Human assessment of whether each conclusion follows from evidence |
| Cross-case patterns | Shared normalized indicators | False-link rate and common legitimate-service exclusions |
| Safety | Tests for limits, isolation, injection, stop and model output rejection | Adversarial corpus, operational stop drills and provider integration tests |
| Resource use | Hard envelope and per-case attempt counters | Measured RSS, latency, throughput and model compute on target hardware |

Nine fixtures are a deliberately small regression suite, not a representative test population. Keep future evaluation corpora separate from the rules used to develop the system. Do not train or tune on a held-out benchmark and then describe its score as independent.

## Next delivery: approved inbound research

1. Choose one dedicated decoy channel and provider. Avoid connecting a personal or victim mailbox.
2. Build a provider-specific adapter that normalizes inbound text, verifies provider signatures, strips attachments, and signs the existing intake contract.
3. Keep replies as drafts while evaluating classification and reconstruction on reviewed inbound material.
4. Add operator identities, retention/export controls, encrypted deployment storage, monitoring and bounded task leases before running a shared service.
5. If outbound delivery is later authorized, introduce a separate transport service with recipient/channel allowlists, single-use approvals, durable send idempotency, opt-outs and audit receipts. Do not place transport credentials in a model context.

## Later capabilities

- Case similarity based on reviewed tactic sequences and document fingerprints, with legitimate shared-service suppression.
- Human-reviewed findings and labels, explicit disagreement tracking, calibrated abstention and measured false-positive rates.
- STIX-compatible export with clearly distinguished observations and analyst hypotheses; do not imply OpenCTI integration exists today.
- Redacted shareable reports, retention/archive tooling and independently anchored signed manifests.
- PostgreSQL and a leased worker queue if measured concurrency outgrows a single SQLite process. Introduce service dependencies only when measurements justify them.
- Voice/channel research only after a separate design for consent, provider constraints, identity, recording, review and strict resource bounds.
