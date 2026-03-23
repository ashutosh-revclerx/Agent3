"""
gemini_client.py
────────────────
Single shared Gemini client using google-genai SDK.
All agents import gemini_json() and gemini_text() from here.

Install: pip install google-genai
Docs:    https://googleapis.github.io/python-genai/
"""
import os, json, re
from pathlib import Path
from google import genai
from google.genai import types
from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_PATH)

# ── Singleton client ──────────────────────────────────────────────────────────
_client: genai.Client | None = None

def get_client() -> genai.Client | None:
    """
    Returns a configured google-genai Client.
    Returns None if GEMINI_API_KEY is not set.
    Agents fall back to rule-based logic when None is returned.
    """
    global _client
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("⚠️  GEMINI_API_KEY not set — agents will use fallback logic")
        return None
    if _client is None:
        _client = genai.Client(api_key=api_key)
        print("✅ Gemini client ready (google-genai SDK)")
    return _client


# ── Model name ────────────────────────────────────────────────────────────────
DEFAULT_MODEL = "gemini-2.5-pro"   # fast + cheap for workshop use
PRO_MODEL     = "gemini-1.5-pro"     # use for complex reasoning (deck builder)


# ── Core helpers ──────────────────────────────────────────────────────────────

def gemini_json(prompt: str, model: str = DEFAULT_MODEL) -> dict | list | None:
    """
    Send a prompt, expect JSON back.
    Strips markdown fences, parses JSON.
    Returns dict/list or None on failure.

    Usage:
        result = gemini_json("Return a JSON object with key 'clusters': [...]")
        if result:
            clusters = result["clusters"]
    """
    client = get_client()
    if not client:
        return None
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,          # low temp = consistent JSON
                max_output_tokens=2048,
            ),
        )
        text = response.text.strip()
        # Strip ```json ... ``` or ``` ... ``` fences
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        return json.loads(text.strip())
    except Exception as e:
        print(f"gemini_json error: {e}")
        return None


def gemini_text(prompt: str, system: str = "",
                model: str = DEFAULT_MODEL) -> str | None:
    """
    Send a prompt, get plain text back.
    Optionally prepend a system instruction.

    Usage:
        output = gemini_text("Summarise this in 2 sentences", system="You are a consultant")
    """
    client = get_client()
    if not client:
        return None
    try:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        response = client.models.generate_content(
            model=model,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.5,
                max_output_tokens=1024,
            ),
        )
        return response.text.strip()
    except Exception as e:
        print(f"gemini_text error: {e}")
        return None


def gemini_json_with_system(prompt: str, system: str,
                             model: str = DEFAULT_MODEL) -> dict | list | None:
    """
    JSON generation with a system instruction prepended.
    Used by agents that need both structured output and role context.

    Usage:
        result = gemini_json_with_system(
            prompt="Generate use case cards as JSON array",
            system="You are an AI strategy consultant for Acme Corp..."
        )
    """
    client = get_client()
    if not client:
        return None
    try:
        full_prompt = f"{system}\n\n{prompt}\n\nReturn ONLY valid JSON, no other text."
        response = client.models.generate_content(
            model=model,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=2048,
            ),
        )
        text = response.text.strip()
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        return json.loads(text.strip())
    except Exception as e:
        print(f"gemini_json_with_system error: {e}")
        return None


def gemini_stream(prompt: str, system: str = "",
                  model: str = DEFAULT_MODEL):
    """
    Streaming text generation — yields chunks as they arrive.
    Use for long-running outputs like deck generation.

    Usage:
        for chunk in gemini_stream("Write a 500-word strategy summary"):
            print(chunk, end="", flush=True)
    """
    client = get_client()
    if not client:
        yield "[GEMINI_API_KEY not set]"
        return
    try:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        for chunk in client.models.generate_content_stream(
            model=model,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.5,
                max_output_tokens=2048,
            ),
        ):
            if chunk.text:
                yield chunk.text
    except Exception as e:
        print(f"gemini_stream error: {e}")
        yield f"[Stream error: {e}]"


def is_available() -> bool:
    """Quick check — returns True if Gemini is configured and reachable."""
    return get_client() is not None
