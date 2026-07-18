from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from .llm_client import classify_text_llm_or_fallback

# 1. Define the State schema structure.
class ComplaintState(TypedDict):
    """
    Dict schema representing the langgraph processing state.
    """
    raw_input: str
    ward_id: int
    complaintType: Optional[str]
    urgency_score: Optional[int]
    originalLanguage: Optional[str]
    translatedText: Optional[str]
    mediaAttachments: Optional[list]
    department_id: Optional[int]
    department_name: Optional[str]
    classification_method: Optional[str]
    reasoning: Optional[str]
    error: Optional[str]
    transcription_success: Optional[bool]

# 2. Hardcoded Deterministic Mapping as approved.
# Allows routing to function predictably and explainably.
COMPLAINT_TYPE_TO_DEPT_MAPPING = {
    "water": {"id": 1, "name": "Water & Sanitation"},
    "electricity": {"id": 2, "name": "Electricity & Power"},
    "roads": {"id": 3, "name": "Roads & Drainage"},
    "sanitation": {"id": 4, "name": "Waste Management"},
    "public safety": {"id": 5, "name": "Public Safety"},
    "other": {"id": 5, "name": "Public Safety"}
}

# 3. Create Graph node processors.
def analyze_input_node(state: ComplaintState) -> dict:
    """
    Analyzes raw input text via LLM or rule-based parser to retrieve complaintType,
    urgency_score, language, reasoning and translation text.
    Bypasses LLM analysis if transcription_success is False.
    """
    if state.get("transcription_success") is False:
        return {
            "complaintType": "Other",
            "urgency_score": 1,
            "originalLanguage": "Unknown",
            "translatedText": state.get("raw_input") or "Fallback: Audio transcription failed.",
            "reasoning": "Audio transcription failed. Complaint is queued for manual triage.",
            "classification_method": "fallback"
        }

    raw_text = state.get("raw_input", "")
    try:
        classification = classify_text_llm_or_fallback(raw_text)
        return {
            "complaintType": classification.get("complaintType", "Other"),
            "urgency_score": classification.get("urgency_score", 3),
            "originalLanguage": state.get("originalLanguage") or classification.get("originalLanguage") or "English",
            "translatedText": classification.get("translatedText") or raw_text,
            "reasoning": classification.get("reasoning", "No rubric reasoning provided."),
            "classification_method": classification.get("classification_method", "fallback")
        }
    except Exception as e:
        return {
            "complaintType": "Other",
            "urgency_score": 3,
            "originalLanguage": state.get("originalLanguage") or "English",
            "translatedText": raw_text,
            "reasoning": f"Node analyzer system error: {str(e)}",
            "classification_method": "fallback",
            "error": str(e)
        }

def route_to_department_node(state: ComplaintState) -> dict:
    """
    Deterministically maps the complaintType extracted in the previous node
    to corresponding department IDs and names.
    """
    complaint_type = state.get("complaintType", "Other")
    type_clean = str(complaint_type).lower().strip()
    
    # Fallback to 'other' if LLM returned an unrecognized type
    if type_clean not in COMPLAINT_TYPE_TO_DEPT_MAPPING:
        type_clean = "other"
        
    mapping = COMPLAINT_TYPE_TO_DEPT_MAPPING[type_clean]
    return {
        "department_id": mapping["id"],
        "department_name": mapping["name"]
    }

# 4. Assemble the LangGraph workflow structure.
workflow = StateGraph(ComplaintState)

workflow.add_node("analyze_input", analyze_input_node)
workflow.add_node("route_to_department", route_to_department_node)

workflow.set_entry_point("analyze_input")
workflow.add_edge("analyze_input", "route_to_department")
workflow.add_edge("route_to_department", END)

# Compile into runnable LangGraph agent.
agent_graph = workflow.compile()
