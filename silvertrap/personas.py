"""Small independent synthetic identities and non-executing dialogue policies."""
PERSONAS = [
    {"id": "margaret", "name": "Margaret Ellis", "age": 73, "initials": "ME", "style": "Warm, patient, asks for plain explanations", "background": "Fictional retired librarian learning to use a tablet.", "opening": "I'm still getting used to this tablet."},
    {"id": "arthur", "name": "Arthur Bennett", "age": 76, "initials": "AB", "style": "Methodical, cautious, keeps handwritten notes", "background": "Fictional retired maintenance planner who likes written instructions.", "opening": "Let me get my notebook."},
    {"id": "evelyn", "name": "Evelyn Hart", "age": 69, "initials": "EH", "style": "Friendly, curious, wants to understand each step", "background": "Fictional retired office administrator and online shopper.", "opening": "I'd like to understand this properly."},
]

QUESTIONS = {
    "contact": ["Could you explain who you represent and what this concerns?", "How did you get in touch with me?", "What is the reference number for this matter?"],
    "trust": ["What department are you with, and what is the reference number?", "How would I verify this through the organization directly?", "What do you need me to understand first?"],
    "manipulation": ["Why does this need to happen so quickly?", "What exactly do you say will happen if I take time to check?", "Could you explain why I should keep this confidential?"],
    "information": ["What information are you requesting, and why is each part needed?", "What would that permission allow someone to do?", "Can you describe the process in words so I can write it down?"],
    "preparation": ["Why is that payment method necessary?", "Who would receive the payment, and what is it for?", "Can you explain how this would resolve the issue?"],
    "theft": ["Could you explain exactly what you want me to do with that code or payment?", "Who would receive it, and why?", "What is the stated reason for this final step?"],
    "exit": ["I need some time to review my notes."],
}


def draft(persona_id, reconstruction, messages):
    persona = next(p for p in PERSONAS if p["id"] == persona_id)
    previous = {m["text"] for m in messages if m["role"] == "persona"}
    stage = reconstruction["current_stage"]
    options = QUESTIONS.get(stage, QUESTIONS["contact"]) + [
        "What is the next step you are asking me to take?", "Could you explain the reason for that?",
        "What else should I understand about how this works?"]
    for question in options:
        candidate = (persona["opening"] + " " if not previous else "") + question
        if candidate not in previous and not any(m.endswith(question) for m in previous):
            return candidate
    return None
