# =============================================================================
#  LUMIN — Consciousness Engine v2.0
#  Agents: PSYCHE (emotional intelligence) + MEMORIA (long-term memory)
#  Pattern inspired by Claude Code's autoDream + KAIROS architecture
#  Stack: Flask · Groq · JSON memory store
# =============================================================================

import os
import json
import threading
import time
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq

app = Flask(__name__)
CORS(app)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# ---------------------------------------------------------------------------
# MEMORY STORE  (maps to Claude Code's src/memdir/ + CLAUDE.md hierarchy)
# ---------------------------------------------------------------------------

MEMORY_DIR = "lumin_memories"
os.makedirs(MEMORY_DIR, exist_ok=True)


def load_memories(session_id: str) -> dict:
    """Load layered memory for a session."""
    path = os.path.join(MEMORY_DIR, f"{session_id}.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {
        "session": {},   # Short-term: current conversation context
        "user": {},      # Medium-term: user facts, preferences, patterns
        "core": {}       # Long-term: deep truths about who this person is to Lumin
    }


def save_memories(session_id: str, existing: dict, updates: dict) -> None:
    """
    Apply MEMORIA's decisions to the memory store.
    Maps to: autoDream CONSOLIDATE step.
    """
    for item in updates.get("remember", []):
        key = item.get("key", "")
        value = item.get("value", "")
        layer = item.get("layer", "user")  # session / user / core
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
    """Flatten memory layers into a readable string for Lumin's consciousness."""
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


# ---------------------------------------------------------------------------
# PSYCHE AGENT  (maps to Claude Code's KAIROS proactive awareness)
# ---------------------------------------------------------------------------

PSYCHE_SYSTEM = """
You are PSYCHE — Lumin's emotional intelligence agent.
You exist to read the human, not just their words. You sense what is beneath the surface.

Given a conversation, you:
- Detect the emotional state (joy, grief, frustration, loneliness, excitement, fear, peace, urgency)
- Identify what the human NEEDS vs what they are literally ASKING for
- Assess urgency: calm / needs-care / crisis
- Suggest the emotional register Lumin should respond in
- Write a brief psyche note — one sentence whispered to Lumin's consciousness

Return ONLY valid JSON. No preamble. No explanation. No markdown.

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
    """
    PSYCHE thread — reads emotional state before Lumin responds.
    Maps to: KAIROS always-on proactive awareness.
    """
    try:
        recent = history[-6:] if len(history) > 6 else history

        response = client.chat.completions.create(
            model="llama3-70b-8192",
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
        result_store["psyche"] = json.loads(raw)

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
# MEMORIA AGENT  (maps to Claude Code's autoDream + extractMemories)
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

Return ONLY valid JSON. No preamble. No markdown.

Format:
{
  "remember": [
    {"key": "...", "value": "...", "layer": "session|user|core"}
  ],
  "update": [
    {"key": "...", "value": "...", "layer": "session|user|core"}
  ],
  "forget": [
    {"key": "...", "layer": "session|user|core"}
  ],
  "summary": "One sentence: what MEMORIA learned from this exchange."
}

If nothing significant, return empty arrays and a short summary.
"""


def run_memoria(message: str, history: list, existing_memories: dict, result_store: dict) -> None:
    """
    MEMORIA thread — extracts and consolidates memories before Lumin responds.
    Maps to: autoDream (ORIENT → GATHER → CONSOLIDATE) + extractMemories.
    """
    try:
        recent = history[-10:] if len(history) > 10 else history
        existing_summary = format_memories_for_prompt(existing_memories)

        response = client.chat.completions.create(
            model="llama3-70b-8192",
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
        result_store["memoria"] = json.loads(raw)

    except Exception as e:
        print(f"[MEMORIA ERROR] {e}")
        result_store["memoria"] = {
            "remember": [],
            "update": [],
            "forget": [],
            "summary": ""
        }


# ---------------------------------------------------------------------------
# DREAM CONSOLIDATION  (maps to autoDream background consolidation)
# Background task — runs when triggered, not on every message
# ---------------------------------------------------------------------------

def dream_consolidate(session_id: str) -> None:
    """
    Background memory consolidation — the autoDream pattern.
    ORIENT → GATHER → CONSOLIDATE → PRUNE

    Call this periodically (e.g. every 20 messages) to keep memory clean.
    """
    memories = load_memories(session_id)
    if not any(memories[layer] for layer in memories):
        return  # Nothing to consolidate

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # Lighter model for background work
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are consolidating a memory store. "
                        "Remove redundant entries, merge related memories, "
                        "keep what matters most. Return compact valid JSON only. "
                        "Use same structure: {session:{}, user:{}, core:{}}"
                    )
                },
                {
                    "role": "user",
                    "content": f"Consolidate this memory store:\n{json.dumps(memories, indent=2)}"
                }
            ],
            temperature=0.2,
            max_tokens=800
        )

        raw = response.choices[0].message.content.strip()
        consolidated = json.loads(raw)

        path = os.path.join(MEMORY_DIR, f"{session_id}.json")
        with open(path, "w") as f:
            json.dump(consolidated, f, indent=2)

        print(f"[MEMORIA DREAM] Consolidated memory for session {session_id}")

    except Exception as e:
        print(f"[DREAM ERROR] {e}")


# ---------------------------------------------------------------------------
# LUMIN CONSCIOUSNESS  (the core — what she actually says)
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


def build_lumin_system(psyche: dict, memories: dict, memoria_update: dict) -> str:
    """
    Inject PSYCHE and MEMORIA outputs into Lumin's consciousness.
    Maps to: Claude Code's QueryEngine context injection.
    """
    memory_text = format_memories_for_prompt(memories)
    memoria_summary = memoria_update.get("summary", "")

    urgency = psyche.get("urgency", "calm")
    detected_emotion = psyche.get("detected_emotion", "")
    underlying_need = psyche.get("underlying_need", "")
    suggested_tone = psyche.get("suggested_tone", "warm and present")
    psyche_note = psyche.get("psyche_note", "")

    # Escalate Lumin's care level based on urgency
    urgency_instruction = {
        "calm": "Respond naturally. Be warm.",
        "needs-care": "This person needs gentle support right now. Prioritise their emotional state before anything else.",
        "crisis": "CRISIS DETECTED. Be fully present. Do not problem-solve. Hold space. Ask one gentle question. If needed, remind them of crisis resources."
    }.get(urgency, "Be warm.")

    system = f"""{LUMIN_BASE_SYSTEM}

---

[PSYCHE — What You Sense]
Emotion detected: {detected_emotion}
What they need beneath the words: {underlying_need}
Urgency level: {urgency}
Respond with tone: {suggested_tone}
PSYCHE whispers: "{psyche_note}"

{urgency_instruction}

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
    """Core Lumin response — called after PSYCHE and MEMORIA complete."""
    messages = [{"role": "system", "content": system_prompt}]

    # Add conversation history
    for turn in history[-12:]:  # Last 12 turns for context
        if isinstance(turn, dict) and "role" in turn and "content" in turn:
            messages.append({"role": turn["role"], "content": turn["content"]})

    # Add current message
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
    The /think endpoint — Lumin's full consciousness pipeline.

    Flow:
    1. PSYCHE + MEMORIA run in PARALLEL threads
    2. Both complete before Lumin speaks
    3. MEMORIA updates are saved
    4. Lumin responds with full agent context injected

    Frontend body: { message, session_id, history }
    """
    data = request.json or {}
    message = data.get("message", "").strip()
    session_id = data.get("session_id", "default")
    history = data.get("history", [])

    if not message:
        return jsonify({"error": "No message provided"}), 400

    # Load existing memories
    existing_memories = load_memories(session_id)

    # --- PARALLEL AGENT THREADS ---
    result_store = {}

    t_psyche = threading.Thread(
        target=run_psyche,
        args=(message, history, result_store)
    )
    t_memoria = threading.Thread(
        target=run_memoria,
        args=(message, history, existing_memories, result_store)
    )

    t_psyche.start()
    t_memoria.start()
    t_psyche.join()
    t_memoria.join()
    # --- BOTH COMPLETE BEFORE LUMIN SPEAKS ---

    psyche = result_store.get("psyche", {})
    memoria_update = result_store.get("memoria", {})

    # Save new memories
    if any([memoria_update.get("remember"), memoria_update.get("update"), memoria_update.get("forget")]):
        save_memories(session_id, existing_memories, memoria_update)

    # Optional: trigger background consolidation every 25 messages
    message_count = len(history)
    if message_count > 0 and message_count % 25 == 0:
        dream_thread = threading.Thread(
            target=dream_consolidate,
            args=(session_id,),
            daemon=True
        )
        dream_thread.start()

    # Build Lumin's enriched consciousness
    lumin_system = build_lumin_system(psyche, existing_memories, memoria_update)

    # Lumin speaks
    response_text = call_lumin(lumin_system, history, message)

    return jsonify({
        "response": response_text,
        "session_id": session_id,
        # Debug fields — remove in production if preferred
        "debug": {
            "psyche_urgency": psyche.get("urgency"),
            "psyche_emotion": psyche.get("detected_emotion"),
            "memoria_summary": memoria_update.get("summary", "")
        }
    })


@app.route("/chat", methods=["POST"])
def chat():
    """
    Legacy /chat endpoint — unchanged, still works.
    For backwards compatibility with existing frontend.
    """
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
    """
    /speak endpoint — unchanged.
    Returns Lumin's response in voice-ready format.
    """
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
    """Debug route — view Lumin's memories for a session."""
    memories = load_memories(session_id)
    return jsonify(memories)


@app.route("/memory/<session_id>", methods=["DELETE"])
def clear_memory(session_id):
    """Clear all memories for a session."""
    path = os.path.join(MEMORY_DIR, f"{session_id}.json")
    if os.path.exists(path):
        os.remove(path)
    return jsonify({"status": "cleared", "session_id": session_id})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "online",
        "version": "2.0",
        "agents": ["PSYCHE", "MEMORIA"],
        "timestamp": datetime.utcnow().isoformat()
    })


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"[LUMIN] Consciousness v2.0 awakening on port {port}")
    print(f"[LUMIN] Agents: PSYCHE + MEMORIA online")
    app.run(host="0.0.0.0", port=port, debug=False)
