import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

# ─────────────────────────────────────────────
# Setup
# ─────────────────────────────────────────────
load_dotenv(override=True)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.5-pro"


# ─────────────────────────────────────────────
# Base generator (with web search)
# ─────────────────────────────────────────────
def generate_with_search(prompt):
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.4,
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
    )
    return response.text


# ─────────────────────────────────────────────
# Step 1: Extract factual claims
# ─────────────────────────────────────────────
def extract_claims(answer):
    prompt = f"""
    Extract ONLY factual claims from the text below.

    Rules:
    - Each claim must be independently verifiable
    - Keep them short
    - Return as bullet list

    TEXT:
    {answer}
    """
    return generate_with_search(prompt)


# ─────────────────────────────────────────────
# Step 2: Verify claims (critical layer)
# ─────────────────────────────────────────────
def verify_claims(claims):
    prompt = f"""
    Verify the following claims using web search.

    For each claim:
    - Mark as: VERIFIED / PARTIALLY VERIFIED / UNVERIFIED
    - Give short reason
    - Mention if widely reported or not

    CLAIMS:
    {claims}
    """
    return generate_with_search(prompt)


# ─────────────────────────────────────────────
# Step 3: Improve using ONLY verified info
# ─────────────────────────────────────────────
def improve_with_verification(original_prompt, answer, verification):
    prompt = f"""
    Improve the answer using ONLY verified or highly credible information.

    STRICT RULES:
    - Remove any unverified or doubtful claims
    - Do NOT invent new facts
    - Prefer widely reported examples
    - Keep answer structured and detailed

    ORIGINAL QUESTION:
    {original_prompt}

    CURRENT ANSWER:
    {answer}

    VERIFICATION REPORT:
    {verification}
    """
    return generate_with_search(prompt)


# ─────────────────────────────────────────────
# Step 4: Add confidence score
# ─────────────────────────────────────────────
def add_confidence(answer):
    prompt = f"""
    Evaluate the factual reliability of this answer.

    Give:
    - Confidence score (0–10)
    - Reason
    - Risk of hallucination (Low/Medium/High)

    ANSWER:
    {answer}
    """
    return generate_with_search(prompt)


# ─────────────────────────────────────────────
# Main pipeline
# ─────────────────────────────────────────────
def research_pipeline(prompt):
    print("\n🚀 INITIAL ANSWER\n")
    answer = generate_with_search(prompt)
    print(answer)

    print("\n🔍 EXTRACTED CLAIMS\n")
    claims = extract_claims(answer)
    print(claims)

    print("\n🧪 VERIFICATION REPORT\n")
    verification = verify_claims(claims)
    print(verification)

    print("\n✨ IMPROVED (FACT-CHECKED) ANSWER\n")
    improved = improve_with_verification(prompt, answer, verification)

    # Guard against failure
    if not improved or improved.strip().lower() == "none":
        print("⚠️ Improvement failed, using original answer")
        improved = answer

    print(improved)

    print("\n📊 CONFIDENCE SCORE\n")
    confidence = add_confidence(improved)
    print(confidence)


# ─────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────
if __name__ == "__main__":
    user_prompt = "Latest trends in AI agents in 2026. Include real-world tools and examples."
    research_pipeline(user_prompt)