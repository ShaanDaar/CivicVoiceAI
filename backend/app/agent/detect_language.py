"""
detect_language.py — Isolated language detection module for CivicVoice AI.

Design intent (AGENTS.md rule):
  Keep LLM classification logic in its own module so models can be swapped easily.
  This module is the single source of truth for language detection — both the
  /transcribe and /voice-complaint endpoints (and the LangGraph graph) call it.

Detection strategy (two-pass):
  Pass 1 — Unicode script range heuristic (fast, offline, deterministic):
    Counts characters in known Unicode blocks and picks the dominant script.
    Covers the most common South Asian languages citizens use.
  Pass 2 — Gemini LLM fallback (only when Pass 1 is inconclusive or returns "Unknown"):
    Sends a short text snippet to Gemini with a language-detection prompt.
    Requires GEMINI_API_KEY in environment.

Supported languages (Pass 1):
  Hindi / Marathi   — Devanagari script    (U+0900–U+097F)
  Bengali           — Bengali script       (U+0980–U+09FF)
  Urdu              — Arabic script        (U+0600–U+06FF)
  Tamil             — Tamil script         (U+0B80–U+0BFF)
  Telugu            — Telugu script        (U+0C00–U+0C7F)
  Kannada           — Kannada script       (U+0C80–U+0CFF)
  Malayalam         — Malayalam script     (U+0D00–U+0D7F)
  Gujarati          — Gujarati script      (U+0A80–U+0AFF)
  Punjabi (Gurmukhī)— Gurmukhi script     (U+0A00–U+0A7F)
  English / Latin   — Basic Latin + Ext   (U+0000–U+024F)

Note: Hindi and Marathi both use Devanagari. We label them "Hindi" generically
since at classification time the distinction doesn't affect routing. The original
transcription is always stored verbatim for a human reviewer.
"""

import os
import json
import requests
from typing import Optional


# ── Unicode range definitions ────────────────────────────────────────────────

# Each entry: (script_name, language_label, start_codepoint, end_codepoint)
SCRIPT_RANGES = [
    ("Devanagari",  "Hindi",     0x0900, 0x097F),
    ("Bengali",     "Bengali",   0x0980, 0x09FF),
    ("Gurmukhi",    "Punjabi",   0x0A00, 0x0A7F),
    ("Gujarati",    "Gujarati",  0x0A80, 0x0AFF),
    ("Oriya",       "Odia",      0x0B00, 0x0B7F),
    ("Tamil",       "Tamil",     0x0B80, 0x0BFF),
    ("Telugu",      "Telugu",    0x0C00, 0x0C7F),
    ("Kannada",     "Kannada",   0x0C80, 0x0CFF),
    ("Malayalam",   "Malayalam", 0x0D00, 0x0D7F),
    ("Arabic",      "Urdu",      0x0600, 0x06FF),
    ("Latin",       "English",   0x0000, 0x024F),
]

# Minimum fraction of characters that must belong to a script to declare it dominant.
# Helps avoid false positives on mixed-language text (e.g. a Hindi sentence with English numbers).
DOMINANCE_THRESHOLD = 0.25


def _count_script_chars(text: str) -> dict:
    """Count how many characters of `text` fall in each defined Unicode script range."""
    counts = {label: 0 for (_, label, _, _) in SCRIPT_RANGES}
    for ch in text:
        cp = ord(ch)
        for (_, label, start, end) in SCRIPT_RANGES:
            if start <= cp <= end:
                counts[label] += 1
                break  # each char counted once
    return counts


def detect_language_heuristic(text: str) -> Optional[str]:
    """
    Pass 1: Fast, offline Unicode heuristic.
    Returns the dominant language label, or None if inconclusive.
    """
    if not text or not text.strip():
        return None

    # Strip whitespace and punctuation for a cleaner character count
    effective_chars = [ch for ch in text if not ch.isspace() and not ch in ".,!?;:'\"()[]{}"]
    if not effective_chars:
        return None

    counts = _count_script_chars("".join(effective_chars))
    total = sum(counts.values())
    if total == 0:
        return None

    # Sort scripts by frequency descending
    sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    top_label, top_count = sorted_counts[0]

    fraction = top_count / total
    if fraction >= DOMINANCE_THRESHOLD and top_label != "English":
        # Non-Latin script dominant → confident detection
        return top_label
    elif fraction >= DOMINANCE_THRESHOLD and top_label == "English":
        # Latin script dominant — could still be English or a romanised Indian language
        # Return English here; Gemini fallback will refine if needed
        return "English"

    return None  # Inconclusive — defer to LLM


def detect_language_llm(text: str) -> str:
    """
    Pass 2: Gemini-based language detection.
    Called when the heuristic is inconclusive or to confirm romanised text.
    Returns a language name string (e.g. "Hindi", "Marathi", "English").
    Falls back to "Unknown" if the API call fails.
    """
    # Load env if needed (support running this module standalone)
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env_path = os.path.join(root_dir, ".env")
    if os.path.exists(env_path) and not os.getenv("GEMINI_API_KEY"):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("[detect_language] No GEMINI_API_KEY — returning 'Unknown'.")
        return "Unknown"

    # Use only the first 300 chars to minimise token usage
    snippet = text[:300]
    prompt = (
        "Identify the primary spoken/written language of this text. "
        "Return ONLY a single JSON object with one field 'language' containing the language name in English "
        "(e.g. 'Hindi', 'Marathi', 'English', 'Bengali', 'Tamil', 'Telugu', 'Kannada', 'Urdu', 'Punjabi', 'Gujarati'). "
        "If truly ambiguous, use 'Unknown'.\n\n"
        f"Text: \"{snippet}\""
    )

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-3.1-flash-lite:generateContent?key={gemini_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    try:
        res = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=8)
        if res.status_code == 200:
            from .llm_client import extract_and_load_json
            data = extract_and_load_json(raw)
            lang = data.get("language", "Unknown").strip()
            print(f"[detect_language] LLM detected: '{lang}'")
            return lang
    except Exception as e:
        print(f"[detect_language] LLM call failed: {e}")

    return "Unknown"


def detect_language(text: str) -> str:
    """
    Main entry point — two-pass language detection.

    Args:
        text: Raw or transcribed text in any language.

    Returns:
        Language name string (e.g. "Hindi", "English", "Tamil", "Unknown").

    Usage:
        from app.agent.detect_language import detect_language
        lang = detect_language("पानी की पाइप लीक हो रही है")  # → "Hindi"
    """
    # Pass 1: fast Unicode heuristic
    result = detect_language_heuristic(text)
    if result:
        print(f"[detect_language] Heuristic detected: '{result}'")
        return result

    # Pass 2: LLM fallback for ambiguous or romanised text
    print("[detect_language] Heuristic inconclusive — calling LLM.")
    return detect_language_llm(text)
