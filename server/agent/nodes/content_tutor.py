"""
Content & Regional Tutor Agent Node (Flexible Multi-Provider AI Inference)
==========================================================================
Combines RAG Educational Retrieval with Culturally Resonant Regional Tutoring:
1. Pulls vector chunks from Pinecone for diagnosed root causes and skill gaps.
2. Generates code-switched technical explanations in Marathi, Hindi, or English.
3. Preserves code syntax and programming keywords in English.
4. Provides interactive Socratic dialogue for follow-up questions (tutor_chat_node).
5. Employs provider-agnostic LLM routing (Gemini primary, NIM fallback) with robust local fallback.
"""

import logging
import os
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage

try:
    from agent.state import StudentState, GroundedResource
    from agent.prompts import format_regional_tutor_prompt, format_tutor_chat_prompt
    from services.rag_service import rag_service
    from core.logger import workflow_log
    from services.tutor_rl import STRATEGY_INSTRUCTIONS
except ImportError:
    from server.agent.state import StudentState, GroundedResource
    from server.agent.prompts import format_regional_tutor_prompt, format_tutor_chat_prompt
    from server.services.rag_service import rag_service
    from server.core.logger import workflow_log
    from server.services.tutor_rl import STRATEGY_INSTRUCTIONS

# Load environment variables
for env_path in [Path("server/.env"), Path(".env"), Path(__file__).parent.parent.parent / ".env"]:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        break

DEFAULT_TUTOR_MODEL = "gemini-3.5-flash-lite"


def get_llm_client(
    model_name: str = DEFAULT_TUTOR_MODEL,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    timeout: float = 20.0
) -> Optional[Any]:
    """
    Generic LLM client factory that instantiates ChatGoogleGenerativeAI or ChatNVIDIA
    based on available API keys and configured model ID.
    """
    google_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    nvidia_key = os.environ.get("NVIDIA_API_KEY")

    if google_key and ("gemini" in model_name.lower() or not nvidia_key):
        try:
            target_model = model_name if "gemini" in model_name.lower() else "gemini-2.0-flash"
            return ChatGoogleGenerativeAI(
                model=target_model,
                google_api_key=google_key,
                temperature=temperature,
                max_output_tokens=max_tokens,
                timeout=timeout
            )
        except Exception as e:
            workflow_log(logging.ERROR, "[LLM]", provider="gemini", model=model_name, status="initialization_failed")

    if nvidia_key:
        try:
            from langchain_nvidia_ai_endpoints import ChatNVIDIA
            return ChatNVIDIA(
                model=model_name,
                api_key=nvidia_key,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout
            )
        except Exception as e:
            workflow_log(logging.ERROR, "[LLM]", provider="nvidia", model=model_name, status="initialization_failed")

    workflow_log(logging.WARNING, "[LLM]", model=model_name, status="no_provider_available")
    return None


# Backward-compatibility alias
get_nvidia_client = get_llm_client


def _clean_thinking_blocks(raw_text: str) -> str:
    """Strips thinking blocks from reasoning models."""
    raw_text = raw_text.strip()
    if "</think>" in raw_text:
        raw_text = raw_text.split("</think>")[-1].strip()
    return raw_text


def extract_clean_text(response: Any) -> str:
    """Extract text from Gemini strings, blocks, dictionaries, and message objects."""
    if response is None:
        return ""
    if isinstance(response, str):
        return response
    if isinstance(response, list):
        return "".join(extract_clean_text(item) for item in response)
    if isinstance(response, dict):
        if "text" in response:
            return extract_clean_text(response["text"])
        if "content" in response:
            return extract_clean_text(response["content"])
        return ""
    content = getattr(response, "content", None)
    if content is not None and content is not response:
        return extract_clean_text(content)
    text = getattr(response, "text", None)
    if text is not None and text is not response:
        return extract_clean_text(text)
    return ""


def _message_text(response: Any) -> str:
    return extract_clean_text(response)


def content_tutor_node(state: StudentState) -> Dict[str, Any]:
    """
    LangGraph Node: Combined Content Retrieval & Regional Tutoring.
    1. Extracts top priority gap and root-cause concepts.
    2. Performs RAG search against Pinecone for educational grounding.
    3. Produces localized explanation in English / Hindi / Marathi.
    """
    priority_gaps = state.get("priority_gaps", [])
    language = state.get("language") or state.get("primary_language", "English")
    target_career = state.get("target_career", "Data Analyst")
    perceived_level = state.get("perceived_level", "Intermediate")

    # 1. Identify key concept to remediate
    target_concept_id = "sql_basics"
    if priority_gaps:
        top_gap = priority_gaps[0]
        # Prefer root-cause concept if diagnosed
        target_concept_id = top_gap.get("root_cause_concept") or top_gap.get("career_skill") or "sql_basics"

    # 2. RAG Retrieval via Pinecone
    gap_ids = [target_concept_id]
    for g in priority_gaps[:3]:
        rc = g.get("root_cause_concept")
        if rc and rc not in gap_ids:
            gap_ids.append(rc)

    raw_resources = rag_service.get_resources_for_gaps(gap_ids, max_per_concept=2)
    grounded_context = rag_service.format_context_for_prompt(raw_resources)

    grounded_items: List[GroundedResource] = []
    for r in raw_resources:
        grounded_items.append({
            "id": r["id"],
            "concept_id": r.get("concept_id", target_concept_id),
            "title": r["title"],
            "resource_type": r.get("resource_type", "article"),
            "url_or_ref": r.get("url_or_ref", ""),
            "content_snippet": r.get("content_snippet", ""),
            "estimated_minutes": r.get("estimated_minutes", 15),
            "difficulty": r.get("difficulty", "intermediate"),
            "tags": r.get("tags", []),
            "similarity_score": r.get("similarity_score")
        })

    # 3. Dynamic Multi-Model LLM Generation via Generic Client
    target_model = state.get("tutor_model") or DEFAULT_TUTOR_MODEL
    llm_client = get_llm_client(model_name=target_model)

    explanation = ""
    if llm_client:
        try:
            prompt_str = format_regional_tutor_prompt(
                concept_id=target_concept_id,
                target_career=target_career,
                language=language,
                perceived_level=perceived_level,
                grounded_context=grounded_context
            )
            messages = [
                SystemMessage(content=f"You are PathForge's Regional AI Mentor. Teach in {language} with code in English."),
                HumanMessage(content=prompt_str)
            ]
            started_at = time.perf_counter()
            response = llm_client.invoke(messages)
            if response:
                explanation = _clean_thinking_blocks(extract_clean_text(response))
                workflow_log(logging.INFO, "[LLM]", model=target_model, duration_ms=round((time.perf_counter() - started_at) * 1000), status="success", schema="tutor_text")
        except Exception as e:
            workflow_log(logging.WARNING, "[LLM]", model=target_model, status="fallback", schema="tutor_text", duration_ms=round((time.perf_counter() - started_at) * 1000) if "started_at" in locals() else None)

    # Fallback explanation if model is offline or empty
    if not explanation:
        concept_name = target_concept_id.replace("_", " ").title()
        reference = grounded_items[0] if grounded_items else None
        reference_text = reference.get("content_snippet", "") if reference else ""
        if language.lower() == "marathi":
            explanation = (
                f"### {concept_name} - संकल्पना स्पष्टीकरण (मराठी)\n\n"
                f"मित्रा, `{concept_name}` ही संकल्पना तुमच्या {target_career} मार्गासाठी महत्त्वाची आहे. आधी मुख्य कल्पना समजून घेऊया, मग छोट्या उदाहरणाने सराव करूया.\n\n"
                f"**अभ्यासासाठी संकेत:** {reference_text or 'ही संकल्पना छोट्या उदाहरणात समजावून घेऊन लगेच स्वतःच्या शब्दांत पुन्हा सांगण्याचा प्रयत्न करा.'}\n\n"
                f"ही संकल्पना स्पष्ट झाली का?"
            )
        elif language.lower() == "hindi":
            explanation = (
                f"### {concept_name} - मुख्य अवधारणा (हिंदी)\n\n"
                f"`{concept_name}` को समझना आपके {target_career} learning path के लिए महत्वपूर्ण है। पहले मुख्य विचार समझें और फिर एक छोटे उदाहरण से अभ्यास करें।\n\n"
                f"**अध्ययन संकेत:** {reference_text or 'इस concept को अपने शब्दों में समझाकर देखें और फिर एक छोटा अभ्यास हल करें।'}\n\n"
                f"क्या यह उदाहरण स्पष्ट है?"
            )
        else:
            explanation = (
                f"### Mastering {concept_name}\n\n"
                f"To excel as a {target_career}, mastering `{concept_name}` is an important step.\n\n"
                f"**Core idea:** {reference_text or 'Break the concept into one small rule, one worked example, and one practice question.'}\n\n"
                f"Review the grounded reference documents below, then ask me about any part that feels unclear."
            )

    return {
        "grounded_resources": grounded_items,
        "tutor_explanation_localized": explanation,
        "next_action": "plan"
    }


def tutor_chat_node(
    state: StudentState,
    student_message: str,
    model_override: Optional[str] = None
) -> Dict[str, Any]:
    """
    Service / Interactive Node for real-time Socratic Q&A tutoring dialogue.
    """
    language = state.get("language") or state.get("primary_language", "English")
    target_career = state.get("target_career", "Data Analyst")
    current_concept = state.get("current_concept_id", "sql_basics")
    priority_gaps = state.get("priority_gaps", [])
    history = state.get("tutor_chat_history", [])

    # Grounding context from state's retrieved resources
    resources = state.get("grounded_resources", [])
    grounded_context = rag_service.format_context_for_prompt(resources)

    target_model = model_override or state.get("tutor_model") or DEFAULT_TUTOR_MODEL
    llm_client = get_llm_client(model_name=target_model)
    tutor_action = state.get("tutor_action") or "DIRECT_EXPLANATION"

    assistant_reply = ""
    if llm_client:
        try:
            system_prompt = format_tutor_chat_prompt(
                target_career=target_career,
                language=language,
                concept_id=current_concept,
                priority_gaps=priority_gaps,
                grounded_context=grounded_context
            )
            system_prompt = (
                f"{system_prompt}\n\nTeaching strategy instruction: "
                f"{STRATEGY_INSTRUCTIONS[tutor_action]}"
            )
            messages = [SystemMessage(content=system_prompt)]
            for turn in history[-4:]:
                if turn.get("role") == "user":
                    messages.append(HumanMessage(content=turn.get("content", "")))
                else:
                    messages.append(AIMessage(content=turn.get("content", "")))
            messages.append(HumanMessage(content=student_message))

            started_at = time.perf_counter()
            response = llm_client.invoke(messages)
            if response:
                assistant_reply = _clean_thinking_blocks(extract_clean_text(response))
                workflow_log(logging.INFO, "[LLM]", model=target_model, duration_ms=round((time.perf_counter() - started_at) * 1000), status="success", schema="tutor_text")
        except Exception as e:
            workflow_log(logging.WARNING, "[LLM]", model=target_model, status="fallback", schema="tutor_text", duration_ms=round((time.perf_counter() - started_at) * 1000) if "started_at" in locals() else None)

    if not assistant_reply:
        assistant_reply = f"I'm here to help you master {current_concept}. Could you share what specific part of this topic feels challenging?"

    new_turns = [
        {"role": "user", "content": student_message},
        {"role": "assistant", "content": assistant_reply}
    ]

    return {
        "tutor_chat_history": new_turns,
        "latest_tutor_reply": assistant_reply
        ,"tutor_action": tutor_action
    }