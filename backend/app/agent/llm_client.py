import os
import json
import requests

def extract_and_load_json(text: str) -> dict:
    """
    Extracts and parses the first JSON object found in text.
    Handles markdown code blocks and leading/trailing non-JSON text.
    """
    text_clean = text.strip()
    
    # Try direct parse first
    try:
        return json.loads(text_clean)
    except Exception:
        pass

    # Look for bounds of the JSON object
    start_idx = text_clean.find("{")
    end_idx = text_clean.rfind("}")
    
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        json_str = text_clean[start_idx:end_idx + 1]
        try:
            return json.loads(json_str)
        except Exception as e:
            # Try cleaning trailing commas or control characters
            try:
                import re
                # Strip trailing commas inside objects/arrays
                json_str_clean = re.sub(r',\s*([\]}])', r'\1', json_str)
                # Strip any control characters or invalid whitespace
                json_str_clean = re.sub(r'[\x00-\x1F\x7F]', '', json_str_clean)
                return json.loads(json_str_clean)
            except Exception:
                pass
            raise e
            
    # Try finding an array instead of object if needed
    start_arr = text_clean.find("[")
    end_arr = text_clean.rfind("]")
    if start_arr != -1 and end_arr != -1 and end_arr > start_arr:
        json_str = text_clean[start_arr:end_arr + 1]
        try:
            return json.loads(json_str)
        except Exception as e:
            raise e
            
    raise ValueError(f"No JSON object or array found in text: {text}")


# Load optional .env file for local development
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_paths = [
    os.path.join(root_dir, ".env"),
    os.path.join(root_dir, "venv", ".env")
]
for ep in env_paths:
    if os.path.exists(ep):
        with open(ep, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()
        break

def classify_rule_based(text: str) -> dict:
    """
    Offline keyword-based fallback engine to classify complaints and calculate urgency score.
    Follows the requested weighted rubric:
      - Base Score: 1
      - Safety Threat keyword matched: +2
      - Duration/Chronicity keyword matched: +1
      - Scale of impact keyword matched: +1
      - Capped at 5
    """
    text_lower = text.lower()
    
    # 1. Determine Category & complaintType
    if any(k in text_lower for k in ["water", "tap", "pipe", "pump", "drinking"]):
        complaint_type = "Water"
    elif any(k in text_lower for k in ["drain", "sewer", "gutter", "block", "manhole"]):
        complaint_type = "Roads"  # mapped to Roads & Drainage department
    elif any(k in text_lower for k in ["electric", "power", "wire", "spark", "light", "shock", "blackout", "transformer"]):
        complaint_type = "Electricity"
    elif any(k in text_lower for k in ["garbage", "trash", "smell", "toilet", "waste", "dump", "dirty", "rubbish", "refuse", "rotting", "pest", "disease", "filth", "toxic"]):
        complaint_type = "Sanitation"
    elif any(k in text_lower for k in ["road", "pothole", "street", "asphalt", "pave", "bridge"]):
        complaint_type = "Roads"
    else:
        complaint_type = "Other"
 
    # 2. Determine Urgency Score (1-5) based on weights
    base_score = 1
    reasons = ["Base (1)"]
    
    # Expanded safety triggers covering electrical hazards, public health risks, and water scarcity
    safety_triggers = [
        # Electrical & Physical Danger
        "spark", "live wire", "shock", "flood", "accident", "damage", "hurt", "injury", "danger", "hazard", "falling",
        # Health & Sanitation Risks (Public Health)
        "contamination", "contaminate", "contaminated", "smell", "smells", "smelling", "smelly", "odor", "odour", "rotting", "rotten", "rot",
        "pest", "pests", "disease", "diseases", "illness", "infection", "filth", "toxic", "health hazard", "sewage", "overflow",
        # Water Scarcity / Critical Wastage
        "leak", "leaking", "leakage", "waste", "wasted", "wastage", "scarcity", "scarce", "shortage", "dry"
    ]
    
    duration_triggers = ["days", "week", "since", "yesterday", "hours", "month", "long time", "ago"]
    scale_triggers = ["street", "block", "market", "school", "everywhere", "community", "all houses", "neighborhood", "public"]
    
    safety_impact = any(k in text_lower for k in safety_triggers)
    duration_mentioned = any(k in text_lower for k in duration_triggers)
    scale_impact = any(k in text_lower for k in scale_triggers)
    
    if safety_impact:
        base_score += 2
        # Find which keyword matched for reasoning visibility
        matched = [k for k in safety_triggers if k in text_lower]
        reasons.append(f"Safety threat: matched '{matched[0]}' (+2)")
    if duration_mentioned:
        base_score += 1
        reasons.append("Duration (+1)")
    if scale_impact:
        base_score += 1
        reasons.append("Public scale (+1)")
        
    urgency_score = min(5, base_score)
    reasoning = f"Urgency: {urgency_score}. Rubric logic: " + " + ".join(reasons) + "."
    
    return {
        "complaintType": complaint_type,
        "urgency_score": urgency_score,
        "originalLanguage": "English",
        "translatedText": text,
        "reasoning": reasoning,
        "classification_method": "fallback"
    }

def classify_text_llm_or_fallback(text: str) -> dict:
    """
    Auto-detects API keys in the environment.
    Routes to:
      1. Gemini API if GEMINI_API_KEY is found (using gemini-3.1-flash-lite).
      2. OpenAI API if OPENAI_API_KEY is found (using gpt-4o-mini).
      3. Rule-based fallback engine if offline.
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
 
    prompt = (
        "You are a specialized civic classifier for SDG 11. Read this citizen complaint raw text:\n"
        f"\"\"\"\n{text}\n\"\"\"\n\n"
        "Generate a JSON object containing exactly these fields:\n"
        "- 'complaintType': Must be exactly one of the following enums:\n"
        "  * 'Water': Water pipeline leaks, drinking water scarcity, pipe bursts.\n"
        "  * 'Sanitation': Garbage accumulation, rotting waste, trash bin overflow, dirty public toilets.\n"
        "  * 'Electricity': Live wire danger, sparking, power outages, damaged streetlights.\n"
        "  * 'Roads': Potholes, broken roads, damaged paving, blocked drainage, open manholes, gutter blockages.\n"
        "  * 'Public Safety': Lack of lighting, general public hazards, structural safety threats.\n"
        "  * 'Other': None of the above.\n"
        "- 'urgency_score': Number from 1 to 5 based on this rubric:\n"
        "  * Base score: 1\n"
        "  * Safety impact (sparks, flooding, physical danger, public health risk like sewage/contamination, water scarcity): +2\n"
        "  * Duration mentioned (e.g. multiple days, since yesterday): +1\n"
        "  * Scale of impact (e.g. whole community, street, market, public area): +1\n"
        "  * Cap the final score between 1 and 5.\n"
        "- 'originalLanguage': Must be exactly one of these language names: 'English', 'Hindi', 'Kannada', 'Tamil', 'Telugu', 'Bengali', 'Marathi', 'Gujarati', 'Urdu', 'Malayalam', 'Punjabi', 'Odia', 'Unknown'.\n"
        "- 'translatedText': The English translation of the input text. If the input text is already in English, copy it verbatim.\n"
        "- 'reasoning': A one-line explanation of the urgency score based on the category definitions and rubric elements found.\n"
        "- 'classification_method': Must be exactly 'llm'.\n\n"
        "Here are reference examples for proper category classification:\n"
        "Example 1:\n"
        "Input: 'The sewage line is blocked and overflows on the road.'\n"
        "Output:\n"
        "{\n"
        "  \"complaintType\": \"Roads\",\n"
        "  \"urgency_score\": 4,\n"
        "  \"originalLanguage\": \"English\",\n"
        "  \"translatedText\": \"The sewage line is blocked and overflows on the road.\",\n"
        "  \"reasoning\": \"Sewage overflow falls under roads/drainage infrastructure. Base (1) + health safety hazard (+2) + public road scale (+1) = 4.\",\n"
        "  \"classification_method\": \"llm\"\n"
        "}\n\n"
        "Example 2:\n"
        "Input: 'Garbage dump has not been cleaned for a week and smell is terrible.'\n"
        "Output:\n"
        "{\n"
        "  \"complaintType\": \"Sanitation\",\n"
        "  \"urgency_score\": 4,\n"
        "  \"originalLanguage\": \"English\",\n"
        "  \"translatedText\": \"Garbage dump has not been cleaned for a week and smell is terrible.\",\n"
        "  \"reasoning\": \"Garbage accumulation falls under sanitation/solid waste. Base (1) + health risk odor (+2) + week duration (+1) = 4.\",\n"
        "  \"classification_method\": \"llm\"\n"
        "}\n\n"
        "Output ONLY the JSON object for the citizen complaint raw text above, formatted cleanly without any codeblock backticks."
    )
 
    if gemini_key:
        try:
            # Connect directly to Gemini API using clean HTTP request
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={gemini_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json"
                }
            }
            res = requests.post(url, headers=headers, json=payload, timeout=10)
            if res.status_code == 200:
                text_out = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                data = extract_and_load_json(text_out)
                data["urgency_score"] = int(data.get("urgency_score", 3))
                data["classification_method"] = "llm"
                return data
        except Exception as e:
            print(f"Gemini API call failed: {e}. Falling back to rule-based classification.")
            
    elif openai_key:
        try:
            # Query standard OpenAI API
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a specialized civic complaint categorization assistant."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"}
            }
            res = requests.post(url, headers=headers, json=payload, timeout=10)
            if res.status_code == 200:
                data = extract_and_load_json(res.json()["choices"][0]["message"]["content"])
                data["urgency_score"] = int(data.get("urgency_score", 3))
                data["classification_method"] = "llm"
                return data
        except Exception as e:
            print(f"OpenAI API call failed: {e}. Falling back to rule-based classification.")
 
    # Offline/No keys fallback
    return classify_rule_based(text)


def transcribe_and_translate_audio(file_bytes: bytes, mime_type: str) -> dict:
    """
    Directly uploads audio bytes to the Gemini API to:
      1. Detect regional language.
      2. Transcribe the text in native script.
      3. Translate it to English.
    Returns:
      {
        "original_transcription": str,
        "english_translation": str,
        "detected_language": str
      }
    """
    import base64
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("No GEMINI_API_KEY found. Falling back to offline mock transcription.")
        return {
            "original_transcription": "",
            "english_translation": "Fallback: Audio transcription failed (No Key).",
            "detected_language": "Unknown",
            "transcription_success": False
        }

    # Encode audio file bytes as base64 string
    audio_base64 = base64.b64encode(file_bytes).decode("utf-8")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={gemini_key}"
    headers = {"Content-Type": "application/json"}
    
    prompt = (
        "You are a civic transcriptionist and translator. The attached voice clip is a citizen complaint. "
        "Perform these tasks:\n"
        "1. Transcribe the audio fully in its original language (e.g. if spoken in Hindi, transcribe in Devnagari/Hindi script).\n"
        "2. Translate that transcription into clear, idiomatic English.\n"
        "3. Detect the primary language spoken (e.g. 'Hindi', 'Marathi', 'English', etc.).\n\n"
        "Generate a JSON object containing exactly these fields:\n"
        "- 'original_transcription': the original language transcription text.\n"
        "- 'english_translation': the English translated text.\n"
        "- 'originalLanguage': name of the detected language (e.g. 'Hindi', 'Marathi', 'Kannada', 'Tamil', 'Telugu', 'Bengali', 'English').\n\n"
        "Output ONLY the JSON object, formatted cleanly without any codeblock backticks."
    )
 
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": audio_base64
                        }
                    },
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
 
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=25)
        if res.status_code == 200:
            text_out = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            data = extract_and_load_json(text_out)
            return {
                "original_transcription": data.get("original_transcription", "").strip(),
                "english_translation": data.get("english_translation", "").strip(),
                "originalLanguage": data.get("originalLanguage", data.get("detected_language", "English")).strip(),
                "transcription_success": True
            }
        else:
            raise Exception(f"Gemini API returned status code {res.status_code}: {res.text}")
    except Exception as e:
        print(f"Gemini audio transcription failed: {e}. Falling back to default.")
        return {
            "original_transcription": "",
            "english_translation": "Fallback: Audio transcription failed. Queued for manual triage.",
            "originalLanguage": "Unknown",
            "transcription_success": False
        }


def translate_to_english(text: str, source_language: str = "Unknown") -> str:
    """
    Translate text from a detected regional language to English.

    Isolated as its own function so the translation model/service can be swapped
    independently of transcription and classification (AGENTS.md rule).

    Args:
        text:             The text to translate (may be in any language).
        source_language:  Hint for the LLM (e.g. "Hindi", "Tamil"). Improves accuracy.

    Returns:
        English translation string, or the original text if translation is unavailable.

    Design note:
        If no Gemini key is configured (offline mode), returns the original text unchanged.
        The calling code should pass the returned value as raw_input to the LangGraph
        classifier only when source_language is non-English; otherwise pass the original.
    """
    # If already English, skip the API call entirely
    if source_language.lower() in ("english", "en"):
        return text

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("[translate_to_english] No GEMINI_API_KEY — returning original text.")
        return text

    prompt = (
        f"Translate the following {source_language} text into clear, idiomatic English. "
        "Output ONLY the English translation with no extra commentary, preamble, or quotes.\n\n"
        f"Text: {text}"
    )

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-3.1-flash-lite:generateContent?key={gemini_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        # Plain text response — we just want the translation string, not JSON
    }
    try:
        res = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=12,
        )
        if res.status_code == 200:
            translation = (
                res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            )
            print(f"[translate_to_english] Translated ({source_language} → English): '{translation[:80]}…'")
            return translation
        else:
            print(f"[translate_to_english] Gemini returned {res.status_code}. Returning original.")
    except Exception as e:
        print(f"[translate_to_english] API call failed: {e}. Returning original.")

    return text


def generate_social_post_draft(text: str, category: str, location: str, has_media: bool = False) -> str:
    """
    Generates a concise, platform-appropriate X (Twitter) social post draft
    using Gemini, OpenAI, or a local fallback template if offline.
    Enforces a strict 280 character limit with truncation.
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    # Map category to tags/handles - use generic fictional placeholders ONLY
    handles = {
        "Water": "@YourCityMunicipal #WaterShortage #SDG11",
        "Sanitation": "@YourCityMunicipal #CleanCity #Sanitation",
        "Electricity": "@YourCityMunicipal #PowerOutage #Electricity",
        "Roads": "@YourCityMunicipal #RoadSafety #Drainage",
        "Public Safety": "@YourCityMunicipal #PublicSafety",
        "Other": "@YourCityMunicipal #CivicVoice #SDG11"
    }
    tag_info = handles.get(category, "@YourCityMunicipal #CivicVoice #SDG11")

    prompt = (
        "You are a helpful civic AI assistant. Write a concise, platform-appropriate draft for a social post (X/Twitter, max 280 characters) "
        "to raise awareness about a citizen's complaint.\n\n"
        f"Complaint: \"{text}\"\n"
        f"Category: {category}\n"
        f"Location: {location}\n"
        f"Contains Media Attachments: {'Yes' if has_media else 'No'}\n\n"
        "Requirements:\n"
        "- Must fit within X/Twitter character limits (strictly less than 280 characters).\n"
        "- State the issue and location clearly.\n"
        f"- Suggest hashtags and handles (use generic fictional handle: @YourCityMunicipal and relevant hashtags: {tag_info}). Do NOT use real handles.\n"
        "- Output ONLY the final raw text draft for the post. Do not add quotes, introductions, or formatting backticks."
    )

    draft = ""
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={gemini_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            res = requests.post(url, headers=headers, json=payload, timeout=10)
            if res.status_code == 200:
                draft = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                draft = draft.strip('"`')
        except Exception as e:
            print(f"Gemini API social post gen failed: {e}")

    elif openai_key:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a civic social media content generator."},
                    {"role": "user", "content": prompt}
                ]
            }
            res = requests.post(url, headers=headers, json=payload, timeout=10)
            if res.status_code == 200:
                draft = res.json()["choices"][0]["message"]["content"].strip().strip('"`')
        except Exception as e:
            print(f"OpenAI API social post gen failed: {e}")

    # Fallback to template if API calls failed or offline
    if not draft:
        media_note = " 📸 Attached." if has_media else ""
        draft = f"⚠️ Alert: {text[:140]}... Location: {location}.{media_note} Need urgent attention: {tag_info}"

    # Strict 280 character limit enforcement
    if len(draft) > 280:
        draft = draft[:277] + "..."

    return draft
