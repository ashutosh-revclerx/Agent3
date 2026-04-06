"""
gemini_client.py
────────────────
Single shared Gemini client using google-genai SDK.
All agents import gemini_json() and gemini_text() from here.

Install: pip install google-genai
Docs:    https://googleapis.github.io/python-genai/
"""
import ast
import os, json, re
from google import genai
from google.genai import types
from env_loader import load_env

load_env()

# ── Singleton client ──────────────────────────────────────────────────────────
_client: genai.Client | None = None


def _response_text(response) -> str:
    """
    Safely extract text from google-genai responses.
    Some responses have `text=None` even when content exists in candidates/parts.
    """
    text = getattr(response, "text", None)
    if isinstance(text, str):
        stripped = text.strip()
        if stripped:
            return stripped

    candidates = getattr(response, "candidates", None) or []
    parts: list[str] = []

    for candidate in candidates:
        content = getattr(candidate, "content", None)
        if not content:
            continue
        for part in getattr(content, "parts", None) or []:
            part_text = getattr(part, "text", None)
            if isinstance(part_text, str) and part_text.strip():
                parts.append(part_text.strip())

    return "\n".join(parts).strip()


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _extract_json_candidate(text: str) -> str:
    start = next((i for i, ch in enumerate(text) if ch in "{["), -1)
    if start == -1:
        return text.strip()

    stack = []
    in_string = False
    escape = False

    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch in "{[":
            stack.append("}" if ch == "{" else "]")
        elif ch in "}]":
            if not stack or ch != stack[-1]:
                continue
            stack.pop()
            if not stack:
                return text[start:i + 1].strip()

    return text[start:].strip()


def _escape_control_chars_in_strings(text: str) -> str:
    chars = []
    in_string = False
    escape = False

    for ch in text:
        if in_string:
            if escape:
                chars.append(ch)
                escape = False
                continue
            if ch == "\\":
                chars.append(ch)
                escape = True
                continue
            if ch == '"':
                chars.append(ch)
                in_string = False
                continue
            if ch == "\n":
                chars.append("\\n")
                continue
            if ch == "\r":
                chars.append("\\r")
                continue
            if ch == "\t":
                chars.append("\\t")
                continue
            chars.append(ch)
            continue

        chars.append(ch)
        if ch == '"':
            in_string = True

    return "".join(chars)


def _parse_json_response(text: str):
    cleaned = _strip_code_fences(text)
    candidates = []

    for candidate in (
        cleaned,
        _extract_json_candidate(cleaned),
        _escape_control_chars_in_strings(cleaned),
        _escape_control_chars_in_strings(_extract_json_candidate(cleaned)),
    ):
        candidate = candidate.strip()
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    last_error = None
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except Exception as exc:
            last_error = exc

    for candidate in candidates:
        try:
            parsed = ast.literal_eval(candidate)
            if isinstance(parsed, (dict, list)):
                return parsed
        except Exception as exc:
            last_error = exc

    if last_error:
        raise last_error
    raise ValueError("Gemini did not return JSON content.")

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
PRO_MODEL     = "gemini-2.5-pro"     # use for complex reasoning (deck builder)


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
                response_mime_type="application/json",
            ),
        )
        text = _response_text(response)
        return _parse_json_response(text)
    except Exception as e:
        print(f"gemini_json error: {e}")
        return None


def gemini_json_with_web_search(prompt: str,
                                model: str = "gemini-2.0-flash") -> dict | list | None:
    """
    Send a prompt and allow Gemini to use Google Search grounding.
    Falls back to plain JSON generation if grounding is unavailable.
    """
    client = get_client()
    if not client:
        return None
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=2048,
                response_mime_type="application/json",
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        text = _response_text(response)
        return _parse_json_response(text)
    except Exception as e:
        print(f"gemini_json_with_web_search error: {e}")
        return gemini_json(prompt, model=DEFAULT_MODEL)


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
        text = _response_text(response)
        return text or None
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
                response_mime_type="application/json",
            ),
        )
        text = _response_text(response)
        return _parse_json_response(text)
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
