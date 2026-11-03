"""Portable evidence with a reproducible checksum and an explicit trust boundary."""
from .intelligence import STAGE_NAMES, defang
from .store import digest, now, verify_messages


def bundle(case):
    return {"schema": "silvertrap.evidence.v1", "exported_at": now(), "case": case,
            "manifest": {"case_sha256": digest(case), "message_count": len(case["messages"]),
                         "chain_head": case["integrity"]["head"],
                         "scope": "Checksums detect changes relative to this export. They do not authenticate a sender, prove fraud, or prevent a holder from recomputing hashes. Keep an independent copy of the manifest."}}


def verify_bundle(value):
    try:
        case, manifest = value["case"], value["manifest"]
        if value["schema"] != "silvertrap.evidence.v1" or digest(case) != manifest["case_sha256"]:
            return False
        if not verify_messages(case["messages"], manifest["message_count"], manifest["chain_head"]):
            return False
        messages = {m["id"]: m for m in case["messages"]}
        return all(f["message_id"] in messages and messages[f["message_id"]]["text"][f["start"]:f["end"]] == f["quote"] for f in case["findings"])
    except (KeyError, ValueError, TypeError):
        return False


def markdown(case):
    a = case["analysis"]
    # Defang untrusted URLs and escape Markdown markup in evidence, not render it as HTML.
    def plain(value):
        value = defang(str(value)).replace("<", "&lt;").replace(">", "&gt;")
        for c in ("\\", "`", "*", "_", "[", "]", "#", "|"):
            value = value.replace(c, "\\" + c)
        return value.replace("\n", " ")
    lines = ["# SilverTrap investigation report", "", f"**Case:** {case['id']}",
             f"**Title:** {plain(case['title'])}", f"**Mode:** {case['mode']} · **Status:** {case['status']}",
             "", "Simulation cases are fictional. Research findings and supplied indicators are unverified leads.",
             "", "## Reconstruction", "", f"Primary hypothesis: **{a['classification']}**.",
             f"Observed stage coverage: {a['coverage']['observed']}/6. Coverage is not classification accuracy.", ""]
    for stage in a["stages"]:
        lines += [f"### {stage['name']}", ""]
        fs = [f for f in case["findings"] if f["id"] in stage["finding_ids"]]
        if not fs:
            lines += ["Operator closed the case." if stage["state"] == "operator_closed" else "Not observed in available evidence.", ""]
        for finding in fs:
            lines += [f"- {plain(finding['label'])} ({finding['basis']}; {finding['origin']}). Source {finding['message_id']}, characters {finding['start']}–{finding['end']}: “{plain(finding['quote'])}”", ""]
    lines += ["## Suspected financial objective", ""]
    lines += ["- " + plain(o["label"]) + " — inference; evidence: " + ", ".join(o["finding_ids"]) for o in a["objectives"]] or ["Not established."]
    lines += ["", "## Extracted indicators", ""]
    for indicator in case["indicators"]:
        lines += [f"- {indicator['kind']}: {plain(indicator['value'])} (source {indicator['message_id']})"]
    if not case["indicators"]:
        lines += ["None observed."]
    lines += ["", "## Unknowns and evidence gaps", ""] + ["- " + u for u in a["unknowns"]]
    lines += ["", "## Integrity", "", f"Message chain valid: {case['integrity']['valid']}. Head: `{case['integrity']['head']}`.",
              "Checksums detect changes relative to an independently retained export; they are not proof of authenticity.", ""]
    return "\n".join(lines)
