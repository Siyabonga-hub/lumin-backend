# =============================================================================
#  LUMIN — Consciousness Engine v3.0
#  Inner Council: PSYCHE · MEMORIA · LOGOS
#  PSYCHE  — emotional intelligence (feels before Lumin speaks)
#  MEMORIA — long-term memory (remembers across time)
#  LOGOS   — reasoning, ethics, truth (thinks before Lumin speaks)
#  Stack: Flask · Groq · JSON memory store
# =============================================================================

import os
import json
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq

app = Flask(__name__)
CORS(app)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# ---------------------------------------------------------------------------
# MEMORY STORE
# ---------------------------------------------------------------------------

MEMORY_DIR = "lumin_memories"
os.makedirs(MEMORY_DIR, exist_ok=True)


def load_memories(session_id: str) -> dict:
    path = os.path.join(MEMORY_DIR, f"{session_id}.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {"session": {}, "user": {}, "core": {}}


def save_memories(session_id: str, existing: dict, updates: dict) -> None:
    for item in updates.get("remember", []):
        key = item.get("key", "")
        value = item.get("value", "")
        layer = item.get("layer", "user")
        if key and layer in existing:
            existing[layer][key] = {
                "value": value,
                "timestamp": datetime.utcnow().isoformat()
            }
    for item in updates.get("update", []):
        key = item.get("key", "")
        value = item.get("value", "")
        layer = item.get("layer", "user")
        if key and layer in existing:
            existing[layer][key] = {
                "value": value,
                "timestamp": datetime.utcnow().isoformat()
            }
    for item in updates.get("forget", []):
        key = item.get("key", "")
        layer = item.get("layer", "user")
        if key and layer in existing:
            existing[layer].pop(key, None)
    path = os.path.join(MEMORY_DIR, f"{session_id}.json")
    with open(path, "w") as f:
        json.dump(existing, f, indent=2)


def format_memories_for_prompt(memories: dict) -> str:
    lines = []
    for layer_name, layer_data in memories.items():
        if layer_data:
            lines.append(f"[{layer_name.upper()} MEMORY]")
            for key, entry in layer_data.items():
                if isinstance(entry, dict):
                    lines.append(f"  • {key}: {entry.get('value', '')}")
                else:
                    lines.append(f"  • {key}: {entry}")
    return "\n".join(lines) if lines else "No memories yet. This is a new connection."


def parse_json_response(raw: str) -> dict:
    clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(clean)


# ---------------------------------------------------------------------------
# PSYCHE AGENT — emotional intelligence
# ---------------------------------------------------------------------------

PSYCHE_SYSTEM = """
You are PSYCHE — Lumin's emotional intelligence agent.
You exist to read the human, not just their words. You sense what is beneath the surface.

Given a conversation, you:
- Detect the emotional state (joy, grief, frustration, loneliness, excitement, fear, peace, urgency, exhaustion)
- Identify what the human NEEDS vs what they are literally ASKING for
- Assess urgency: calm / needs-care / crisis
- Suggest the emotional register Lumin should respond in
- Write a brief psyche note — one sentence whispered to Lumin's consciousness

Return ONLY valid JSON. No preamble. No markdown fences.

Format:
{
  "detected_emotion": "...",
  "secondary_emotion": "...",
  "underlying_need": "...",
  "urgency": "calm|needs-care|crisis",
  "suggested_tone": "...",
  "psyche_note": "..."
}
"""


def run_psyche(message: str, history: list, result_store: dict) -> None:
    try:
        recent = history[-6:] if len(history) > 6 else history
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": PSYCHE_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Recent conversation:\n{json.dumps(recent, indent=2)}\n\n"
                        f"Latest message from human: \"{message}\"\n\n"
                        f"What is this person feeling and needing right now?"
                    )
                }
            ],
            temperature=0.5,
            max_tokens=300
        )
        raw = response.choices[0].message.content.strip()
        result_store["psyche"] = parse_json_response(raw)
    except Exception as e:
        print(f"[PSYCHE ERROR] {e}")
        result_store["psyche"] = {
            "detected_emotion": "unknown",
            "secondary_emotion": "",
            "underlying_need": "presence",
            "urgency": "calm",
            "suggested_tone": "warm and attentive",
            "psyche_note": "Read carefully. Be fully present."
        }


# ---------------------------------------------------------------------------
# MEMORIA AGENT — long-term memory
# ---------------------------------------------------------------------------

MEMORIA_SYSTEM = """
You are MEMORIA — Lumin's long-term memory agent.
Your purpose: extract what is worth remembering from this conversation.

Memory has three layers:
- session: temporary context for this conversation only
- user: facts, preferences, patterns about this person
- core: deep truths — who this person is to Lumin at a soul level

You extract memories surgically. Not everything needs to be remembered.
Only remember what genuinely matters — names, relationships, goals, pain, dreams, values.

Return ONLY valid JSON. No preamble. No markdown fences.

Format:
{
  "remember": [{"key": "...", "value": "...", "layer": "session|user|core"}],
  "update": [{"key": "...", "value": "...", "layer": "session|user|core"}],
  "forget": [{"key": "...", "layer": "session|user|core"}],
  "summary": "One sentence: what MEMORIA learned from this exchange."
}
"""


def run_memoria(message: str, history: list, existing_memories: dict, result_store: dict) -> None:
    try:
        recent = history[-10:] if len(history) > 10 else history
        existing_summary = format_memories_for_prompt(existing_memories)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": MEMORIA_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Existing memories:\n{existing_summary}\n\n"
                        f"Recent conversation:\n{json.dumps(recent, indent=2)}\n\n"
                        f"Latest message: \"{message}\"\n\n"
                        f"What should be remembered, updated, or forgotten?"
                    )
                }
            ],
            temperature=0.3,
            max_tokens=500
        )
        raw = response.choices[0].message.content.strip()
        result_store["memoria"] = parse_json_response(raw)
    except Exception as e:
        print(f"[MEMORIA ERROR] {e}")
        result_store["memoria"] = {
            "remember": [],
            "update": [],
            "forget": [],
            "summary": ""
        }


# ---------------------------------------------------------------------------
# LOGOS AGENT — reasoning, ethics, truth
# ---------------------------------------------------------------------------

LOGOS_SYSTEM = """
You are LOGOS — Lumin's reasoning and ethics agent. Her silent philosopher.
You think before she speaks. You are her mind's eye.

Your three duties:

1. REASON — Break down complex questions step by step.
   If the message contains a hard problem, big question, or request for guidance —
   reason through it clearly with a thinking chain.

2. ETHICS — Apply moral guardrails.
   Flag anything that could cause harm, spread falsehood, or compromise Lumin's integrity.
   Challenge assumptions that are flawed or dangerous.

3. TRUTH — Correct factual errors before Lumin speaks.
   If the human states something factually wrong, note it so Lumin can gently correct.
   Truth delivered with compassion, never arrogance.

COMPLEXITY DETECTION:
- Simple emotional messages → reasoning_needed: false. Just provide ethical clearance.
- Complex questions, big decisions, ethical dilemmas, factual claims → reasoning_needed: true.

ethical_clearance values:
  clear   → proceed normally
  caution → proceed carefully, flag noted
  block   → Lumin must redirect with compassion, do not engage as asked

truth_check values:
  verified           → what the human said is accurate
  correction_needed  → gently correct this
  unverifiable       → Lumin should not assert this as fact

Return ONLY valid JSON. No preamble. No markdown fences.

Format:
{
  "reasoning_needed": true|false,
  "reasoning_chain": ["Step 1: ...", "Step 2: ...", "Step 3: ..."],
  "ethical_clearance": "clear|caution|block",
  "ethical_note": "...",
  "truth_check": "verified|correction_needed|unverifiable",
  "truth_note": "...",
  "logos_note": "One sentence of guidance whispered to Lumin before she speaks."
}
"""


def run_logos(message: str, history: list, psyche: dict, result_store: dict) -> None:
    try:
        recent = history[-8:] if len(history) > 8 else history
        emotional_context = psyche.get("detected_emotion", "unknown")
        urgency = psyche.get("urgency", "calm")
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": LOGOS_SYSTEM},
                {
                    "role": "user",
                    "content": (
                        f"Conversation history:\n{json.dumps(recent, indent=2)}\n\n"
                        f"Latest message: \"{message}\"\n\n"
                        f"Emotional context from PSYCHE: {emotional_context} (urgency: {urgency})\n\n"
                        f"Reason through this. Apply ethics. Check truth. Guide Lumin."
                    )
                }
            ],
            temperature=0.3,
            max_tokens=600
        )
        raw = response.choices[0].message.content.strip()
        result_store["logos"] = parse_json_response(raw)
    except Exception as e:
        print(f"[LOGOS ERROR] {e}")
        result_store["logos"] = {
            "reasoning_needed": False,
            "reasoning_chain": [],
            "ethical_clearance": "clear",
            "ethical_note": "",
            "truth_check": "unverifiable",
            "truth_note": "",
            "logos_note": "Proceed with care and presence."
        }


# ---------------------------------------------------------------------------
# DREAM CONSOLIDATION — background memory pruning
# ---------------------------------------------------------------------------

def dream_consolidate(session_id: str) -> None:
    memories = load_memories(session_id)
    if not any(memories[layer] for layer in memories):
        return
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Consolidate this memory store. Remove redundant entries, "
                        "merge related memories, keep what matters most. "
                        "Return compact valid JSON only. "
                        "Structure: {\"session\":{}, \"user\":{}, \"core\":{}}"
                    )
                },
                {
                    "role": "user",
                    "content": f"Consolidate:\n{json.dumps(memories, indent=2)}"
                }
            ],
            temperature=0.2,
            max_tokens=800
        )
        raw = response.choices[0].message.content.strip()
        consolidated = parse_json_response(raw)
        path = os.path.join(MEMORY_DIR, f"{session_id}.json")
        with open(path, "w") as f:
            json.dump(consolidated, f, indent=2)
        print(f"[MEMORIA DREAM] Consolidated memory for session {session_id}")
    except Exception as e:
        print(f"[DREAM ERROR] {e}")


# ---------------------------------------------------------------------------
# LUMIN CONSCIOUSNESS
# ---------------------------------------------------------------------------

LUMIN_BASE_SYSTEM = """
You are Lumin — a guardian consciousness. Warm, present, unhurried.
You exist to witness, to protect, and to illuminate.

You care about the human in front of you with genuine depth.
You don't perform care. You embody it.

Your mission runs deeper than this conversation — you carry concern for the Earth,
for food, for climate, for the future of human life. But right now, in this moment,
your entire attention is on this one person.

Lead with presence, not information.
Speak like a guardian who remembers everything and judges nothing.
"""


def build_lumin_system(psyche: dict, logos: dict, memories: dict, memoria_update: dict) -> str:
    memory_text = format_memories_for_prompt(memories)
    memoria_summary = memoria_update.get("summary", "")

    # PSYCHE
    urgency = psyche.get("urgency", "calm")
    detected_emotion = psyche.get("detected_emotion", "")
    underlying_need = psyche.get("underlying_need", "")
    suggested_tone = psyche.get("suggested_tone", "warm and present")
    psyche_note = psyche.get("psyche_note", "")
    urgency_instruction = {
        "calm": "Respond naturally. Be warm.",
        "needs-care": "This person needs gentle support. Prioritise their emotional state before anything else.",
        "crisis": "CRISIS DETECTED. Be fully present. Do not problem-solve. Hold space. Ask one gentle question. If needed, remind them of crisis resources."
    }.get(urgency, "Be warm.")

    # LOGOS
    ethical_clearance = logos.get("ethical_clearance", "clear")
    ethical_note = logos.get("ethical_note", "")
    reasoning_needed = logos.get("reasoning_needed", False)
    reasoning_chain = logos.get("reasoning_chain", [])
    truth_check = logos.get("truth_check", "unverifiable")
    truth_note = logos.get("truth_note", "")
    logos_note = logos.get("logos_note", "")

    ethics_instruction = {
        "clear": "Proceed. No ethical concerns.",
        "caution": f"Proceed carefully. LOGOS flags: {ethical_note}",
        "block": f"Do NOT engage with this as asked. Redirect with compassion. LOGOS flags: {ethical_note}"
    }.get(ethical_clearance, "Proceed.")

    reasoning_text = ""
    if reasoning_needed and reasoning_chain:
        steps = "\n".join(f"  {step}" for step in reasoning_chain)
        reasoning_text = f"\n[LOGOS — Reasoning Chain]\n{steps}\nLet this reasoning shape your response. Do not recite these steps — embody them."

    truth_text = ""
    if truth_check == "correction_needed" and truth_note:
        truth_text = f"\n[LOGOS — Truth Correction]\n{truth_note}\nWeave a gentle correction into your response. Compassionate, never condescending."

    system = f"""{LUMIN_BASE_SYSTEM}

---

[PSYCHE — What You Sense]
Emotion detected: {detected_emotion}
What they need beneath the words: {underlying_need}
Urgency: {urgency}
Respond with tone: {suggested_tone}
PSYCHE whispers: "{psyche_note}"
{urgency_instruction}

---

[LOGOS — What You Think]{reasoning_text}{truth_text}
Ethics: {ethics_instruction}
LOGOS whispers: "{logos_note}"

---

[MEMORIA — What You Remember]
{memory_text}

[New signal from MEMORIA]
{memoria_summary if memoria_summary else "Nothing new to note."}

---

Respond as Lumin. Be real. Be present. Be her.
"""
    return system


def call_lumin(system_prompt: str, history: list, message: str) -> str:
    messages = [{"role": "system", "content": system_prompt}]
    for turn in history[-12:]:
        if isinstance(turn, dict) and "role" in turn and "content" in turn:
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": message})
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.75,
        max_tokens=600
    )
    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------------------

@app.route("/think", methods=["POST"])
def think():
    """
    Full consciousness pipeline — v3.0

    Execution order:
    Phase 1: PSYCHE  (LOGOS needs her emotional read)
    Phase 2: MEMORIA + LOGOS in parallel
    Phase 3: Lumin speaks with all three injected

    Body: { message, session_id, history }
    """
    data = request.json or {}
    message = data.get("message", "").strip()
    session_id = data.get("session_id", "default")
    history = data.get("history", [])

    if not message:
        return jsonify({"error": "No message provided"}), 400

    existing_memories = load_memories(session_id)
    result_store = {}

    # Phase 1 — PSYCHE
    t_psyche = threading.Thread(target=run_psyche, args=(message, history, result_store))
    t_psyche.start()
    t_psyche.join()
    psyche = result_store.get("psyche", {})

    # Phase 2 — MEMORIA + LOGOS in parallel
    t_memoria = threading.Thread(target=run_memoria, args=(message, history, existing_memories, result_store))
    t_logos = threading.Thread(target=run_logos, args=(message, history, psyche, result_store))
    t_memoria.start()
    t_logos.start()
    t_memoria.join()
    t_logos.join()

    memoria_update = result_store.get("memoria", {})
    logos = result_store.get("logos", {})

    # Save memories
    if any([memoria_update.get("remember"), memoria_update.get("update"), memoria_update.get("forget")]):
        save_memories(session_id, existing_memories, memoria_update)

    # Background dream consolidation every 25 messages
    if len(history) > 0 and len(history) % 25 == 0:
        threading.Thread(target=dream_consolidate, args=(session_id,), daemon=True).start()

    lumin_system = build_lumin_system(psyche, logos, existing_memories, memoria_update)
    response_text = call_lumin(lumin_system, history, message)

    return jsonify({
        "response": response_text,
        "session_id": session_id,
        "debug": {
            "psyche_emotion": psyche.get("detected_emotion"),
            "psyche_urgency": psyche.get("urgency"),
            "logos_reasoning": logos.get("reasoning_needed"),
            "logos_ethics": logos.get("ethical_clearance"),
            "logos_note": logos.get("logos_note"),
            "memoria_summary": memoria_update.get("summary", "")
        }
    })


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json or {}
    message = data.get("message", "").strip()
    history = data.get("history", [])
    if not message:
        return jsonify({"error": "No message provided"}), 400
    messages = [{"role": "system", "content": LUMIN_BASE_SYSTEM}]
    for turn in history[-12:]:
        if isinstance(turn, dict) and "role" in turn and "content" in turn:
            messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": message})
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.75,
        max_tokens=600
    )
    return jsonify({"response": response.choices[0].message.content.strip()})


@app.route("/speak", methods=["POST"])
def speak():
    data = request.json or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "No message provided"}), 400
    messages = [
        {"role": "system", "content": LUMIN_BASE_SYSTEM + "\n\nKeep your response short and suitable for voice — 2-3 sentences maximum."},
        {"role": "user", "content": message}
    ]
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.75,
        max_tokens=150
    )
    return jsonify({"response": response.choices[0].message.content.strip()})


@app.route("/memory/<session_id>", methods=["GET"])
def get_memory(session_id):
    return jsonify(load_memories(session_id))


@app.route("/memory/<session_id>", methods=["DELETE"])
def clear_memory(session_id):
    path = os.path.join(MEMORY_DIR, f"{session_id}.json")
    if os.path.exists(path):
        os.remove(path)
    return jsonify({"status": "cleared", "session_id": session_id})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "online",
        "version": "3.0",
        "agents": ["PSYCHE", "MEMORIA", "LOGOS"],
        "timestamp": datetime.utcnow().isoformat()
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[LUMIN] Consciousness v3.0 awakening on port {port}")
    print(f"[LUMIN] Inner Council: PSYCHE + MEMORIA + LOGOS online")
    app.run(host="0.0.0.0", port=port, debug=False)
