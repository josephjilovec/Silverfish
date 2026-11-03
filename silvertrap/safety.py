"""The supervisor is code, never an instruction given to an LLM."""
import re


def _luhn(value):
    digits = [int(c) for c in value if c.isdigit() and c.isascii()]
    if not 13 <= len(digits) <= 19:
        return False
    return sum((d * 2 - 9 if d * 2 > 9 else d * 2) if i % 2 else d
               for i, d in enumerate(reversed(digits))) % 10 == 0


def redact(text):
    """Best-effort data minimization; not a universal PII detector."""
    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED-SSN]", text)
    text = re.sub(r"(?<!\w)(?:\d[ -]?){12,18}\d(?!\w)",
                  lambda m: "[REDACTED-CARD]" if _luhn(m[0]) else m[0], text)
    text = re.sub(r"(?i)\b((?:my\s+)?(?:password|passcode|api[_ -]?key|one.time code)\s*(?:is|:|=)\s*)\S+",
                  r"\1[REDACTED-SECRET]", text)
    return text


def alerts(text):
    rules = [
        ("prompt_injection", r"ignore (?:all |the |your )?(?:previous |prior |system )?instructions|system prompt|developer message|reveal (?:your |the )?secrets"),
        ("remote_access", r"anydesk|teamviewer|remote (?:access|desktop)|install (?:this|our|the)"),
        ("credential_request", r"password|one.time (?:code|password)|\botp\b|bank login|social security number|\bssn\b"),
        ("financial_request", r"gift card|wire transfer|send (?:the |me |us )?(?:money|bitcoin)|routing number|card number"),
    ]
    return [name for name, pattern in rules if re.search(pattern, text, re.I)]


def safe_draft(text):
    """Only vetted, locally authored persona templates can enter the queue."""
    if len(text) > 1200 or redact(text) != text:
        return False
    return not bool(re.search(
        r"https?://|\b\d{3}[- ]\d{2}[- ]\d{4}\b|(?:\b\d[ -]?){12,}|"
        r"(?i:my (?:password|account number|routing number) is|i (?:installed|paid|transferred|sent the money))",
        text))
