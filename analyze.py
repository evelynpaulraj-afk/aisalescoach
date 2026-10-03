from dotenv import load_dotenv
load_dotenv()
"""
analyze.py
Takes a diarized transcript and produces the sentence-by-sentence
conversation journey, then the final score + coaching report.
Calls Google's Gemini API (free tier) instead of a local model.

NOTE: this call is remote regardless of which model you use here - it does
NOT reduce the backend's RAM usage. The RAM-heavy parts of the pipeline are
Whisper and pyannote, which run locally inside the server's own container
no matter which LLM API this file calls. Swapping Groq for Gemini is a
model-quality/cost choice, not a fix for Render's free-tier RAM limit.

Get a free API key at https://aistudio.google.com/apikey and set it as
GEMINI_API_KEY.
"""

import json
import os
import time
from google import genai
from google.genai import types

from prompts import build_role_identification_prompt, build_analysis_prompt, build_final_report_prompt

ANALYSIS_DIR = "data/analysis"

# Gemini's current lightweight, free-tier-friendly model. gemini-2.5-flash
# was retired for new users; Google's own API error pointed to this one as
# the replacement. Check ai.google.dev/gemini-api/docs/models if this one
# changes again.
MODEL = "gemini-3.8-flash"

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


def call_llm(prompt: str, retries: int = 2, max_api_retries: int = 4) -> dict:
    """
    Sends a prompt to Gemini and parses the JSON response.

    Handles two different failure modes separately:
    - Transient server errors (503 "overloaded", 429 "rate limited") are
      retried with exponential backoff, since these are Google-side and
      usually clear up within seconds to a couple minutes.
    - Malformed JSON in an otherwise-successful response is retried
      immediately (no backoff needed - that's a model output issue, not
      a server issue).
    Permanent errors (e.g. 404 bad model name, 401 bad API key) are not
    retried - they fail immediately since retrying won't fix them.
    """
    last_error = None

    for attempt in range(retries + 1):
        # --- Call the API, with backoff retry for transient errors only ---
        response = None
        for api_attempt in range(max_api_retries + 1):
            try:
                response = client.models.generate_content(
                    model=MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.2,  # lower temperature = more consistent scoring
                        response_mime_type="application/json",  # constrains output to valid JSON
                    ),
                )
                break  # success
            except Exception as e:
                error_text = str(e)
                is_transient = "503" in error_text or "UNAVAILABLE" in error_text or "429" in error_text
                if is_transient and api_attempt < max_api_retries:
                    wait = 2 ** api_attempt  # 1s, 2s, 4s, 8s, 16s
                    print(f"[analyze] Gemini overloaded/rate-limited, retrying in {wait}s "
                          f"(attempt {api_attempt + 1}/{max_api_retries})...")
                    time.sleep(wait)
                    continue
                raise  # permanent error, or out of retries - let it propagate

        raw_text = response.text.strip()
        clean = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        try:
            return json.loads(clean)
        except json.JSONDecodeError as e:
            last_error = e
            print(f"[analyze] JSON parse failed (attempt {attempt + 1}/{retries + 1}), retrying...")

    raise RuntimeError(f"LLM did not return valid JSON after {retries + 1} attempts: {last_error}")


def identify_roles(diarized_transcript: list[dict]) -> dict:
    """
    Looks at the first several turns and maps SPEAKER_00/SPEAKER_01
    labels to "salesperson"/"customer".
    """
    sample = diarized_transcript[:6]
    prompt = build_role_identification_prompt(sample)
    return call_llm(prompt)


def apply_roles(diarized_transcript: list[dict], role_map: dict) -> list[dict]:
    for seg in diarized_transcript:
        seg["role"] = role_map.get(seg["speaker"], "unknown")
    return diarized_transcript


def build_conversation_journey(transcript_with_roles: list[dict]) -> list[dict]:
    """
    Walks through the transcript turn by turn, preserving raw order.
    For every SALESPERSON statement, runs the full analysis prompt using
    prior context and the customer's actual NEXT customer reply — found
    by scanning forward past any intervening salesperson turns, rather
    than blindly grabbing the next item in the list (which breaks when
    the salesperson speaks multiple times in a row before the customer
    responds).
    """
    journey = []

    for i, turn in enumerate(transcript_with_roles):
        if turn["role"] == "customer":
            journey.append({
                "timestamp": turn["start"],
                "speaker": "CUSTOMER",
                "statement": turn["text"],
            })
            continue

        # role == "salesperson"
        prior_context = transcript_with_roles[:i]

        next_customer_turn = None
        for future in transcript_with_roles[i + 1:]:
            if future["role"] == "customer":
                next_customer_turn = future
                break

        prompt = build_analysis_prompt(turn, prior_context, next_customer_turn)
        analysis = call_llm(prompt)

        journey.append({
            "timestamp": turn["start"],
            "speaker": "SALES",
            "statement": turn["text"],
            "analysis": analysis,
        })

        print(f"[analyze] Processed turn at {turn['start']:.2f}s - score: {analysis.get('score')}")

    return journey


def generate_final_report(journey: list[dict]) -> dict:
    prompt = build_final_report_prompt(journey)
    return call_llm(prompt)


def analyze_and_cache(audio_path: str, diarized_transcript: list[dict]) -> dict:
    """
    Full pipeline: role identification -> turn-by-turn journey -> final report.
    Caches the complete result.
    """
    os.makedirs(ANALYSIS_DIR, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    cache_path = os.path.join(ANALYSIS_DIR, f"{base_name}_report.json")

    if os.path.exists(cache_path):
        print(f"[analyze] Loading cached analysis: {cache_path}")
        with open(cache_path, "r") as f:
            return json.load(f)

    print("[analyze] Identifying speaker roles...")
    role_map = identify_roles(diarized_transcript)
    print(f"[analyze] Role map: {role_map}")

    transcript_with_roles = apply_roles(diarized_transcript, role_map)

    print("[analyze] Building conversation journey...")
    journey = build_conversation_journey(transcript_with_roles)

    print("[analyze] Generating final report...")
    final_report = generate_final_report(journey)

    result = {"journey": journey, "final_report": final_report}

    with open(cache_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"[analyze] Saved full analysis: {cache_path}")

    return result