# SilverTrap

**See how a suspected scam works, one message at a time.**

SilverTrap turns a conversation into a map of the sender's tactics, information requests, and possible financial objective. Click any finding to inspect its source message. Start with fictional sample cases, then try your own research messages.

**No API key or paid AI service is needed.** The default analysis uses local programmed rules. You can optionally add real AI analysis through a local Ollama model. SilverTrap does not use your ChatGPT subscription. This version runs simulations and controlled research; it does not contact people or send external replies.

[Windows setup](#start-here-windows) · [Your first test](#try-your-first-investigation) · [Local AI with Ollama](#add-local-ai-with-ollama-optional) · [Troubleshooting](#common-problems) · [Technical reference](#technical-reference)

## Start here: Windows

### 1. Check Python and Git

Open **PowerShell** and run these two commands:

```powershell
python --version
git --version
```

You need **Python 3.11 or newer** and Git. If both commands show version numbers and Python is recent enough, continue to step 2. You do not need an administrator PowerShell window.

<details>
<summary>Python or Git is missing? Open the installation instructions.</summary>

If Python is missing or older than 3.11, install Python 3.13:

```powershell
winget install --exact --id Python.Python.3.13 --scope user
```

For Git, use the [official Git for Windows installer](https://git-scm.com/downloads/win). If `winget` is unavailable, use the [official Python Windows downloads](https://www.python.org/downloads/windows/). When a Python installer offers **Add Python to PATH**, select it.

**Close PowerShell and reopen it after installation**, then run the two version checks again. Windows needs a new terminal to pick up installation changes.

</details>

### 2. Download SilverTrap onto your Desktop

If you have access to this private repository and Git authentication is already connected, paste this entire block into PowerShell:

```powershell
$desktop = [Environment]::GetFolderPath('Desktop')
Set-Location $desktop
git clone https://github.com/josephjilovec/Silverfish.git
Set-Location Silverfish
```

The Desktop command also handles a Desktop managed by OneDrive. The repository folder is called **Silverfish**; the application inside it is **SilverTrap**.

**Already downloaded it?** Open that folder instead of cloning again. To reopen the default Desktop copy:

```powershell
Set-Location (Join-Path ([Environment]::GetFolderPath('Desktop')) 'Silverfish')
```

<details>
<summary>Prefer downloading a ZIP instead of using Git?</summary>

On this repository page, select **Code → Download ZIP**, extract it, and open the extracted folder containing `README.md`, `start.ps1`, and the `silvertrap` folder. Click File Explorer's address bar, type `powershell`, and press Enter. Your terminal will open in the correct project folder. Continue with step 3.

</details>

### 3. Start the application

From the project folder, run:

```powershell
python -m silvertrap serve --seed
```

The terminal will show the app address and an **Operator access code**. Open **[http://127.0.0.1:8787](http://127.0.0.1:8787)** in your browser, paste that code into the login screen, and select **Open command center**. Your code is generated on your computer; keep it private.

**Leave the PowerShell window open while using SilverTrap.** No `pip install`, Node setup, or database installation is needed. On an empty database, `--seed` creates three fictional sample investigations so you can test the product immediately.

## Try your first investigation

1. On **Overview**, open **The urgent support call**.
2. Click **Information gathering** in the stage map. Read the findings, then select **Inspect source** to see the exact message behind one.
3. Open **Evidence & gaps** to inspect the suspected financial objective, chronological findings, and unanswered questions.
4. Select **Report** to download a readable report, or **Evidence** to download a JSON evidence package.

**Want to watch a case develop?** Select **New investigation → Simulation**, choose a scenario, **uncheck “Reconstruct the complete scenario now,”** and select **Create investigation**. Click **Next exchange** to progress one exchange at a time. No external party is contacted.

The three sample cases are already complete scenarios, so their **Next exchange** buttons are disabled. Create a fresh step-by-step simulation to use that button.

### What the main screens mean

| Screen | Use it to… |
| --- | --- |
| **Overview** | See your cases and open a sample investigation. |
| **Investigations** | Search cases or create a new one. |
| **Reconstruction** inside a case | Select a scam stage and inspect the evidence supporting it. |
| **Transcript** inside a case | Read the conversation in order. |
| **Evidence & gaps** inside a case | Review findings, hypotheses, chronology, and unknowns. |
| **Review queue** inside a case | Inspect proposed persona questions and record local review decisions. |
| **Indicator library** | Find contact details and websites appearing across cases. |
| **Controls & limits** | Inspect resource limits or use the emergency stop. |

**Observed phrase** means a rule matched the source text. **Hypothesis** means a possible interpretation, not a verified fact. **Unobserved** means a stage lacks evidence. The persona conversations use fictional identities; only inbound source messages feed the analysis. Research approvals do not send messages.

To try outside material, choose **New investigation → Manual research**, name your case, and paste one source message into **Add an inbound research message**. Select **Analyze message**, then add later messages in their original order. Avoid importing real passwords or financial credentials.

## Add local AI with Ollama (optional)

**You can use and test the entire core app without this step.** Enabling Ollama adds a manually requested AI second opinion. The programmed rules still analyze messages automatically; the model runs when you click its button.

### 1. Install Ollama and download a local model

Install [Ollama for Windows](https://ollama.com/download/windows), open the Ollama application, and open a new PowerShell window. If you already have a local model installed, run `ollama list` and use its exact name in step 2.

For a concrete example, download the local [Llama 3.2 3B model](https://ollama.com/library/llama3.2):

```powershell
ollama pull llama3.2:3b
ollama list
```

The download needs an internet connection and disk space; running it also uses your computer's RAM and processing power. This is an example local model, not a measured accuracy recommendation. Other installed local models can be used by substituting their exact names below.

### 2. Restart SilverTrap with that model enabled

If SilverTrap is running, press **Ctrl+C** in its terminal first. From the project folder in that same PowerShell window, run:

```powershell
$env:SILVERTRAP_OLLAMA_MODEL = "llama3.2:3b"
python -m silvertrap serve --seed
```

Keep Ollama running in the background. Reopen the dashboard and log in. Inside an investigation, **Local model second opinion** should now be enabled. Click it, then review the returned hypotheses in **Evidence & gaps**. A valid model response may contain no additional hypotheses.

With a fully local model such as the example above, this uses **no paid API tokens and no ChatGPT quota**. SilverTrap sends the evidence window to Ollama on your own computer at `127.0.0.1:11434`. Avoid cloud-routed models if your requirement is local processing.

The `$env:` setting applies to that PowerShell session. Repeat the two-line startup block when starting from a new terminal. Local model attempts are limited to four per case; repeated analysis of unchanged evidence uses the cache. A slow model can exceed the current timeout, and malformed or unsupported quotes are rejected; the default findings remain available.

## Stop, reopen, or update

**Stop:** press **Ctrl+C** in the server terminal. Your cases save automatically in the project's local `data` folder.

**Reopen your Desktop copy:**

```powershell
Set-Location (Join-Path ([Environment]::GetFolderPath('Desktop')) 'Silverfish')
python -m silvertrap serve --seed
```

For local AI, set `SILVERTRAP_OLLAMA_MODEL` as shown above before starting. `--seed` does not duplicate the sample cases when the database already contains cases.

**Update a Git clone:** stop the server, open PowerShell in the project folder, and run `git pull --ff-only`, then start SilverTrap again. Your `data` folder is excluded from Git. A ZIP download does not support `git pull`.

## Common problems

| What you see | What to do |
| --- | --- |
| `py` is not recognized | Use the documented `python` commands instead; the separate `py` launcher is not required. |
| `python` is not recognized, or opens the Microsoft Store | Install Python, reopen PowerShell, and check `python --version`. |
| `No module named silvertrap` | Open PowerShell in the folder containing `README.md` and the `silvertrap` folder, not `C:\Windows\System32`. |
| Git says `Repository not found` or authentication fails | This repository is private. Confirm that your GitHub account has access and Git is authenticated. |
| Git says the `Silverfish` folder already exists | Open the existing project folder instead of cloning into it again. |
| The dashboard cannot be reached | Keep the server terminal open and use the exact address it prints. |
| The access code is rejected | Copy the code from the currently running server terminal. |
| `Next exchange` is disabled | The sample is complete, the case is paused/closed, or emergency stop is active. For a new walkthrough, create a simulation with the automatic-completion box unchecked. |
| The local-model button is disabled | Set the model environment variable in the terminal that starts SilverTrap, then restart it. Closed cases and emergency stop also disable analysis. |
| Local model is unavailable or its evidence fails validation | Check that Ollama is running and that `ollama list` includes the configured model. A timeout or rejected output consumes an attempt; unchanged failed evidence is not automatically retried. |

## macOS or Linux

Clone the repository, change into its folder, and run:

```sh
git clone https://github.com/josephjilovec/Silverfish.git
cd Silverfish
python3 -m silvertrap serve --seed
```

Python 3.11 or newer is required. Open the address printed in the terminal and use its access code. For an installed local Ollama model, start with:

```sh
SILVERTRAP_OLLAMA_MODEL=llama3.2:3b python3 -m silvertrap serve --seed
```

![SilverTrap command center with synthetic cases and cross-case indicators](docs/images/command-center.jpg)

## Technical reference

The steps above are enough to use and test the product. Developers and operators can expand the reference below for architecture, tests, exports, integration boundaries, and deployment options.

<details>
<summary>Open developer and advanced operating documentation</summary>

## What you can do

- **Run nine synthetic scenarios:** tech support, Social Security, Medicare, romance, investment, government, grandparent emergency, a benign reminder, and a prompt-injection test.
- **Advance one exchange or a full scenario.** Each persona uses independent case history and stage-aware questions without repeating previously used templates.
- **Explore seven scam stages.** Select a stage, inspect observed phrases, and jump to the originating message. View the chronological findings alongside the fixed stage reference map.
- **Separate observation from inference.** Classification and financial objectives are hypotheses; unobserved phases and unknown ownership stay explicit.
- **Correlate indicators across cases.** Extract URLs, domains, email addresses, US-format phone numbers, and cryptocurrency-address candidates. Shared infrastructure is a lead, not proof of a network.
- **Create manual research cases or import JSON transcripts.** Only inbound messages feed the intelligence engine. Imports are read-only after creation.
- **Review persona drafts locally.** In simulations an approved draft can enter the fictional transcript. In research cases approval records a review decision; it does not send a message.
- **Pause or close cases and apply a persistent emergency stop.** Closed cases stay read-only. Emergency stop invalidates pending drafts and blocks intake, simulation, approvals, and model calls.
- **Export Markdown reports and JSON evidence packages.** Check source offsets, message chains, and a whole-case checksum; make consistent SQLite backups through the CLI.
- **Optionally request a local model second opinion.** No model is called by default. Ollama hypotheses must pass structural and literal-evidence validation and remain labeled as inferences.

## Resource-friendly architecture

| Component | v0.1 implementation | Reason |
| --- | --- | --- |
| Orchestrator | Python standard library | One small process; straightforward deployment |
| Persistent storage | SQLite with WAL and transactions | No separate database or queue services |
| Command center | HTML, CSS, vanilla JavaScript | No frontend dependency tree or build step |
| Analyst roles | Incremental deterministic modules | No seven-model-call cascade per message |
| Optional local analysis | Ollama, one bounded call | Explicit opt-in; no paid provider installed |
| Inbound integration seam | HMAC-signed JSON intake | Disabled unless configured; no outbound transport |
| Verification | `unittest`, synthetic evaluation | Runs offline with no test dependencies |

The seven roles are Persona Agent, Behavioral Analyst, Scam Classifier, Financial Analyst, Intelligence Extractor, Reconstruction Agent, and Safety Supervisor. They are specialized code paths sharing a small process, not seven independent LLM instances. The optional model supplies additional hypotheses; it cannot control the persona, execute tools, change controls, or send messages.

Default limits: **200 cases, 80 messages per case, 8 KiB per message, 128 KiB stored text per case, 200 MiB database write budget, four model attempts per case, and one concurrent model request.** These are explicit constants in `silvertrap/config.py`. The HTTP server permits at most 16 concurrent requests. Model responses are capped at 64 KiB, requested output at 1,000 tokens, and the HTTP request timeout at 25 seconds; cancellation of model computation is not guaranteed by a client timeout.

## Verify the build

```sh
python -m unittest discover -s tests -v
python scripts/evaluate.py
```

Evaluation uses nine fixtures designed alongside the rules. Passing it demonstrates regression consistency, **not independent real-world accuracy**. The tests cover source provenance, case isolation, idempotency, resource limits, immutable closed cases, redaction, prompt injection, stop persistence, export tampering, local-model validation, signed intake, authentication, and concurrent simulation requests. CI repeats the offline checks on Python 3.11, 3.12, and 3.13.

## CLI

```sh
python -m silvertrap --help
python -m silvertrap simulate tech-support
python -m silvertrap export ST-your-case-id exports/case.json
python -m silvertrap verify exports/case.json
python -m silvertrap backup backups/silvertrap.sqlite3
python -m silvertrap --data-dir ./research-data serve --seed
```

An evidence package includes the case, messages, findings, indicators, reconstruction, and a manifest. Checksums detect changes relative to a retained export; they do not establish sender authenticity or prevent someone with the full file from recalculating hashes. Keep an independent copy of the manifest. Message and indicator offsets are zero-based **Unicode code-point indices**, end exclusive, in the stored redacted text.

## Optional local intelligence

If you already have Ollama running locally with a model installed, set its exact local model name before starting SilverTrap:

```powershell
$env:SILVERTRAP_OLLAMA_MODEL = "your-installed-local-model"
python -m silvertrap serve
```

```sh
SILVERTRAP_OLLAMA_MODEL=your-installed-local-model python3 -m silvertrap serve
```

The **Local model second opinion** button sends a bounded recent evidence window to the fixed loopback endpoint `http://127.0.0.1:11434/api/chat`. No arbitrary model URL is accepted, redirects and environment proxies are disabled, and the request grants no tools. The application does not download models. Run a local model rather than a cloud-routed model if your requirement is offline processing. Model RAM and compute are additional to the core app's usage.

Responses are cached by case, model, and transcript hash. Attempts are reserved before calling the provider; failures consume the attempt and are not automatically retried. Evidence changes or an emergency stop while inference runs cause its results to be discarded. Local-model hypotheses require human interpretation even when their quotes are valid. See the [Ollama chat contract](https://docs.ollama.com/api/chat) and [structured output documentation](https://docs.ollama.com/capabilities/structured-outputs).

## Transcript imports

Use **New investigation → Import transcript**:

```json
{
  "messages": [
    {"role": "inbound", "text": "This is Microsoft support. Respond immediately."},
    {"role": "persona", "text": "Could you explain what this concerns?"},
    {"role": "inbound", "text": "Buy gift cards and send me the gift card codes."}
  ]
}
```

The import role `persona` means the non-inbound side of the transcript; imported text is supplied evidence, not proof that SilverTrap generated that message. Do not import real credentials. Best-effort redaction removes common SSN, Luhn-valid card, and explicit secret-value patterns before storage. It does not anonymize every name, phone number, or other personal detail. The original message is not retained; its SHA-256 fingerprint is retained with the redacted record.

## Hybrid deployment path

The simulation-first foundation is implemented. A disabled-by-default, signed intake endpoint is available for a dedicated inbound adapter. It only accepts messages into an existing controlled research case. It does not connect to a mailbox, phone carrier, victim account, or outbound messaging service. [The API guide](docs/API.md) defines signatures, timestamp expiry, and replay protection.

Production inbound operation still needs a provider-specific adapter, channel authorization, TLS and operator identity management, durable delivery semantics, independent evaluation, retention policy, and operational review. Autonomous live replies, voice calls, attachments, browser execution, payments, and reporting to third parties are not implemented. The system does not retaliate, threaten, provoke, or access a sender's systems.

## Docker option

```sh
docker compose up --build
docker compose logs silvertrap
```

The compose service binds only to the host loopback address, runs as a non-root user, keeps data in a named volume, and caps the application at 256 MiB and one CPU. Copy the access code from its logs. These container limits exclude any separately running local model. Docker execution is an optional packaging path; the standard-library app is the primary tested runtime.

## Further technical detail

- [Architecture and data contracts](docs/ARCHITECTURE.md)
- [API and signed intake](docs/API.md)
- [Security and operating boundaries](docs/SECURITY.md)
- [Evaluation and next milestones](docs/ROADMAP.md)

This repository is intended to stay private. Runtime evidence, tokens, logs, and personal data belong outside source control.

</details>
