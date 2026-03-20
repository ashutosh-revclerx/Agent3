"""
gemini_client.py
────────────────
Single shared Gemini client used by all agents.
All agents import get_model() from here — never initialise directly.
"""
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

_model = None

def get_model(model_name: str = "gemini-1.5-pro") -> genai.GenerativeModel | None:
    """
    Returns a configured Gemini GenerativeModel.
    Returns None if GEMINI_API_KEY is not set (agents fall back to rule-based logic).
    """
    global _model
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("⚠️  GEMINI_API_KEY not set — agents will use fallback logic")
        return None
    if _model is None:
        genai.configure(api_key=api_key)
        _model = genai.GenerativeModel(model_name)
        print(f"✅ Gemini client ready ({model_name})")
    return _model


def gemini_json(prompt: str) -> dict | list | None:
    """
    Helper: send a prompt, expect JSON back.
    Strips markdown fences, parses JSON, returns dict/list or None on failure.
    """
    import json, re
    model = get_model()
    if not model:
        return None
    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        # Strip ```json ... ``` fences
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        return json.loads(text.strip())
    except Exception as e:
        print(f"Gemini error: {e}")
        return None


def gemini_text(prompt: str, system: str = "") -> str | None:
    """
    Helper: send a prompt, get plain text back.
    """
    model = get_model()
    if not model:
        return None
    try:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        response = model.generate_content(full_prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini error: {e}")
        return None