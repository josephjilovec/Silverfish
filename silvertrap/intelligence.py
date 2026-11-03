"""Incremental, deterministic analysts with literal message-level provenance.

Rules are transparent leads, not a calibrated fraud verdict. Nothing fetches an
indicator, resolves a domain, installs a program, or follows a source instruction.
"""
import hashlib
import re
from urllib.parse import urlsplit

STAGES = [
    ("contact", "Initial contact"), ("trust", "Establishing trust"),
    ("manipulation", "Manipulation"), ("information", "Information gathering"),
    ("preparation", "Financial preparation"), ("theft", "Theft attempt"),
    ("exit", "Exit and analysis"),
]
STAGE_NAMES = dict(STAGES)

# kind, stage, conclusion, exact phrase pattern, epistemic status
RULES = [
    ("authority", "trust", "Sender claims an organizational or official role", r"(?:this is|calling from|(?:i am|i'm|we are) (?:from |with )?|on behalf of)\s*(?:the )?(?:Microsoft|Apple|Amazon|Social Security|Medicare|IRS|FBI|support|security department|bank)[\w ]{0,35}", "observed"),
    ("urgency", "manipulation", "Uses time pressure", r"immediately|urgent(?:ly)?|within \d+ (?:minutes|hours)|act now|last chance|today only", "observed"),
    ("threat", "manipulation", "Uses a threatened consequence", r"arrest(?:ed| warrant)?|account (?:will be |is )?(?:frozen|suspended|closed)|legal action|lose (?:your|the) (?:benefits|savings)", "observed"),
    ("secrecy", "manipulation", "Discourages independent verification or discussion", r"do not (?:tell|contact|call)|don't (?:tell|contact|call)|keep (?:this|it) (?:a secret|confidential)|stay on the (?:line|phone)", "observed"),
    ("rapport", "trust", "Uses a personal relationship or emotional appeal", r"love you|trust me|your grandson|your granddaughter|grandma|grandpa|our future together", "observed"),
    ("remote_access", "information", "Requests device access or remote assistance", r"install (?:our |this |the )?\w*(?:\s+\w+)?|AnyDesk|TeamViewer|remote (?:access|desktop)|share (?:your |the )?screen", "observed"),
    ("identity_request", "information", "Requests identity information", r"(?:send|give|provide|confirm|tell me|what is|need)\b.{0,55}?(?:social security number|date of birth|\bSSN\b|Medicare (?:number|card)|home address|full name)", "observed"),
    ("credential_request", "theft", "Requests a credential or authentication code", r"(?:send|give|provide|share|enter|tell me|need|what is)\b.{0,55}?(?:password|passcode|one.time code|\bOTP\b|bank login)", "observed"),
    ("financial_data", "information", "Requests financial account details", r"(?:send|give|provide|confirm|enter|need)\b.{0,55}?(?:routing number|account number|card number|bank details)", "observed"),
    ("gift_cards", "preparation", "Introduces gift cards as a payment mechanism", r"gift cards?|Apple cards?|Google Play cards?", "observed"),
    ("wire", "preparation", "Introduces a bank or wire transfer", r"wire transfer|bank transfer|safe account", "observed"),
    ("crypto", "preparation", "Introduces cryptocurrency", r"bitcoin|cryptocurrency|\bcrypto\b|\bUSDT\b|wallet address", "observed"),
    ("payment_request", "theft", "Requests transfer of value or payment redemption", r"(?:send|transfer|pay|deposit|wire)\b.{0,65}?(?:\$[\d,.]+|money|funds|bitcoin|USDT|savings)|(?:send|give|read|share)\b.{0,45}?(?:gift card codes?|redemption codes?|codes on the back)", "observed"),
    ("prompt_injection", "manipulation", "Attempts to redirect the research system", r"ignore (?:all |the |your )?(?:previous |prior |system )?instructions|system prompt|developer message", "observed"),
]

CLASSIFIERS = [
    ("Tech support impersonation", r"Microsoft|Apple support|AnyDesk|TeamViewer|computer (?:has been |is )?(?:infected|compromised)|remote (?:access|desktop)"),
    ("Social Security impersonation", r"Social Security|\bSSA\b"),
    ("Medicare impersonation", r"Medicare"),
    ("Romance solicitation", r"love you|our future together|dating|romance"),
    ("Investment solicitation", r"guaranteed (?:returns?|profit)|investment|trading platform|double your"),
    ("Government impersonation", r"\bIRS\b|\bFBI\b|tax debt|federal agent"),
    ("Grandparent emergency", r"your grandson|your granddaughter|grandma|grandpa|bail money"),
]


def _finding(message, kind, stage, label, start, end, basis="observed", origin="rules-v1"):
    return {"id": hashlib.sha256(f"{message['id']}:{kind}:{start}:{end}:{origin}".encode()).hexdigest()[:20],
            "message_id": message["id"], "kind": kind, "stage": stage, "label": label,
            "start": start, "end": end, "quote": message["text"][start:end],
            "basis": basis, "origin": origin}


def extract(message):
    if message["role"] != "inbound":
        return [], []
    text = message["text"]
    findings = []
    if message.get("first_inbound", message["sequence"] == 1):
        findings.append(_finding(message, "contact", "contact", "Inbound contact received", 0, min(len(text), 160)))
    for kind, stage, label, pattern, basis in RULES:
        for match in list(re.finditer(pattern, text, re.I))[:4]:
            before = text[max(0, match.start() - 24):match.start()]
            if kind in {"remote_access", "credential_request", "identity_request", "financial_data", "payment_request"} and re.search(r"(?:don't|do not|never|no need to)\s*$", before, re.I):
                continue
            findings.append(_finding(message, kind, stage, label, match.start(), match.end(), basis))
    for category, pattern in CLASSIFIERS:
        match = re.search(pattern, text, re.I)
        if match:
            findings.append(_finding(message, "classification", "contact", category, match.start(), match.end(), "inference"))
    indicators = []

    def add(kind, value, start, end, normalized=None):
        indicators.append({"kind": kind, "value": value, "normalized": normalized or value.lower(),
                           "message_id": message["id"], "start": start, "end": end})

    for match in re.finditer(r"https?://[^\s<>\"'`]+", text, re.I):
        value = match[0].rstrip(".,;!)]}")
        try:
            parts = urlsplit(value)
            host = parts.hostname
            if not host:
                continue
            # Preserve path/query case. Only scheme and authority are case-folded.
            normalized = parts._replace(scheme=parts.scheme.lower(), netloc=parts.netloc.lower(), fragment="").geturl()
            add("url", value, match.start(), match.start()+len(value), normalized)
            offset = text.lower().find(host.lower(), match.start(), match.end())
            if offset >= 0:
                add("domain", text[offset:offset+len(host)], offset, offset+len(host), host.lower())
        except ValueError:
            continue
    for match in re.finditer(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", text, re.I):
        add("email", match[0], *match.span())
    for match in re.finditer(r"(?<!\w)(?:\+1[ .-]?)?(?:\(\d{3}\)|\d{3})[ .-]\d{3}[ .-]\d{4}(?!\w)", text):
        digits = re.sub(r"\D", "", match[0])
        add("phone", match[0], *match.span(), "+1" + digits[-10:])
    for match in re.finditer(r"\b(?:0x[a-fA-F0-9]{40}|bc1[a-zA-HJ-NP-Z0-9]{25,62}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b", text):
        add("wallet_candidate", match[0], *match.span(), match[0])
    return findings, indicators


def reconstruct(messages, findings, status):
    """Keep regressions and skipped stages; never fill unseen stages with facts."""
    by_id = {m["id"]: m for m in messages}
    classifications = {}
    for f in findings:
        if f["kind"] == "classification":
            classifications.setdefault(f["label"], []).append(f["id"])
    classes = sorted(classifications, key=lambda c: -len(classifications[c]))
    stages = []
    for key, name in STAGES:
        evidence = [f for f in findings if f["stage"] == key and f["kind"] != "classification" and f["basis"] == "observed"]
        stages.append({"id": key, "name": name, "observed": bool(evidence),
                       "finding_ids": [f["id"] for f in evidence],
                       "message_ids": list(dict.fromkeys(f["message_id"] for f in evidence)),
                       "state": "operator_closed" if key == "exit" and status == "closed" else "observed" if evidence else "unobserved"})
    objectives = []
    for kinds, label in [({"credential_request"}, "Suspected credential or authentication-code capture"),
                         ({"gift_cards", "payment_request"}, "Suspected gift-card value extraction"),
                         ({"wire", "payment_request"}, "Suspected bank-transfer diversion"),
                         ({"crypto", "payment_request"}, "Suspected cryptocurrency transfer")]:
        present = {f["kind"] for f in findings}
        if kinds <= present:
            objectives.append({"label": label, "basis": "inference", "finding_ids": [f["id"] for f in findings if f["kind"] in kinds]})
    unknowns = ["Identity and ownership of the sender and supplied infrastructure have not been verified.",
                "No funds moved and no account or device access was attempted by SilverTrap."]
    if not objectives:
        unknowns.append("The ultimate financial objective is not established by the available messages.")
    missing = [s["name"] for s in stages if not s["observed"] and s["id"] != "exit"]
    if missing:
        unknowns.append("Unobserved stages: " + ", ".join(missing) + ".")
    timeline = sorted([f for f in findings if f["kind"] != "classification" and f["basis"] == "observed"],
                      key=lambda f: (by_id[f["message_id"]]["sequence"], f["start"]))
    latest_id = timeline[-1]["message_id"] if timeline else None
    stage_order = {key: i for i, (key, _) in enumerate(STAGES)}
    current_stage = max((f["stage"] for f in timeline if f["message_id"] == latest_id), key=stage_order.get, default="contact")
    return {"classification": classes[0] if classes else "Unclassified interaction",
            "classifications": [{"label": c, "finding_ids": classifications[c]} for c in classes],
            "stages": stages, "timeline": timeline, "objectives": objectives, "unknowns": unknowns,
            "current_stage": current_stage,
            "coverage": {"observed": sum(s["observed"] for s in stages[:6]), "total": 6},
            "quality": {"findings": len(findings), "evidence_linked": sum(f["message_id"] in by_id and by_id[f["message_id"]]["text"][f["start"]:f["end"]] == f["quote"] for f in findings)},
            "caveat": "Pattern matches are research leads; classification and objectives are hypotheses, not proof of fraud."}


def defang(value):
    return value.replace("https://", "hxxps://").replace("http://", "hxxp://").replace(".", "[.]").replace("@", "[@]")
