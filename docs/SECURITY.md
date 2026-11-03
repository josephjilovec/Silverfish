# Operating boundaries

SilverTrap is a local, single-operator research prototype. Its default execution path is offline deterministic simulation. A private Git repository controls access to source code; it does not secure an exposed running server.

## Enforced in code

- Operator APIs require a high-entropy bearer code. The CLI generates one when needed. The default listener is loopback.
- Untrusted text is escaped when displayed. Browser policy blocks third-party scripts, framing, and automatic external fetches. Static serving is an explicit four-path allowlist, not a directory browser.
- Inbound source messages cannot execute commands, call tools, follow URLs, grant access, make payments, query accounts, or download attachments. Those capabilities are not implemented.
- Persona templates do not contain real credentials or account data. Imported persona-side messages cannot become adversary indicators or classifier evidence.
- Common credential-value, SSN, and payment-card patterns are redacted before storage. Other personal information may remain. There is no automatic full anonymization.
- Drafts are case-bound. New evidence, a pause/close, or emergency stop supersedes pending drafts. Research approvals are local review records, never sends.
- Prompt-injection pattern matches pause the case. This is defense in depth; the actual boundary is the absence of execution or delivery capabilities. Pattern detection is not a complete injection detector.
- Size, turn, model-call, case-count, database and request-concurrency limits are explicit. Database operations use parameters, foreign keys and transactions.
- Optional signed intake requires a timestamped HMAC and payload-bound event idempotency. It accepts text only into an active controlled research case.
- Optional model analysis uses a fixed loopback endpoint, disables redirects and environment proxies, has no tools, validates source quotes, and labels interpretations as hypotheses. Its application code has one concurrent call and no automatic retries.
- Runtime evidence, local access codes, environment files and backups are excluded from Git.

## Honest limits

- Rule matches are not a fraud verdict. Negation, multilingual phrasing, ambiguous organizations, unusual payment requests and obfuscated indicators can cause errors or omissions.
- Source-quote validation does not establish that an interpretation follows from the quote. An operator must review hypotheses before using them.
- Hash chains and export checksums are not digital signatures, trusted timestamps, or proof of sender authenticity. Retain an independent manifest; an administrator can rewrite both a database and its hashes.
- SQLite content is not encrypted by this application. Use an encrypted device and appropriate local access controls. The access code is a local secret stored separately from the database; rotate it by stopping the server and replacing the configured or generated code.
- The standard-library HTTP server is intended for local controlled research. There is no multi-user identity provider, RBAC, session revocation service, internet-facing rate limiter, or production perimeter.
- A local endpoint can still route to cloud inference if its Ollama deployment/model does so. Use a fully local model and control its own network access if offline processing is required.
- A client-side timeout bounds the application's wait, not necessarily the model server's compute. The core container limits do not include the model server.
- Request logs omit message content and authorization; local terminal startup prints the operator code so the operator can log in. Protect that terminal and container logs.

No outbound investigation network is activated by this build. Before adding real channels, design provider permissions, authentication, deliverability/replay behavior, opt-out handling, retention and redaction, operator review, independent benchmarks, and operational monitoring. Keep the objective evidence collection and fraud prevention; do not add retaliation or unauthorized access.
