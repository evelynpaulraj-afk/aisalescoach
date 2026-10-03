"""
prompts.py
Builds the prompts sent to the LLM for each stage of analysis.
This is where your coaching rubric lives - edit this file to change
how the AI evaluates statements, not analyze.py.
"""

import json

MESSAGE_LABELS = [
    "Positive", "Conversational", "Consultative", "Customer-focused",
    "Product-focused", "Salesy", "Scripted", "Boring", "Aggressive",
    "Defensive", "Generic", "Credible", "Empathetic",
]

TONE_TRAITS = [
    "Tone", "Energy", "Confidence", "Pace", "Hesitation",
    "Enthusiasm", "Flatness", "Aggressiveness", "Warmth",
]


def build_role_identification_prompt(sample_turns: list[dict]) -> str:
    """
    Used once at the start of a call to map SPEAKER_00/SPEAKER_01
    to salesperson/customer, based on word patterns.
    """
    turns_text = "\n".join(f'{t["speaker"]}: "{t["text"]}"' for t in sample_turns)
    return f"""Below are the first few turns of a sales conversation. Speaker labels
are generic (SPEAKER_00, SPEAKER_01). Based on the content of what each
speaker says, identify which label is the SALESPERSON and which is the
CUSTOMER.

Turns:
{turns_text}

Respond ONLY with valid JSON in this exact format, no other text:
{{"SPEAKER_00": "salesperson" or "customer", "SPEAKER_01": "salesperson" or "customer"}}
"""


def build_analysis_prompt(current_turn: dict, prior_context: list[dict], next_turn: dict | None) -> str:
    """
    The core per-exchange analysis prompt. Called once per salesperson
    statement. Includes prior conversation context and, when available,
    the customer's actual next response, so the model can judge reaction
    in context rather than analyzing the transcript flat/out of order.
    """
    context_text = "\n".join(
        f'[{t["role"].upper()}] "{t["text"]}"' for t in prior_context[-4:]
    ) or "(this is the first statement in the conversation)"

    next_text = f'"{next_turn["text"]}"' if next_turn else "(no response yet / end of conversation)"

    return f"""You are an AI sales conversation coach. You analyze one salesperson
statement at a time, in the context of the conversation so far, the way
an experienced sales manager listening live would.

CONVERSATION SO FAR:
{context_text}

SALESPERSON STATEMENT TO ANALYZE:
"{current_turn["text"]}"

CUSTOMER'S ACTUAL NEXT RESPONSE (for context only - do not just restate it):
{next_text}

Evaluate the salesperson statement across these dimensions:

A. WHAT WAS SAID - the actual words and message intent.
B. HOW IT WAS SAID - estimate tone characteristics if inferable from word
   choice and phrasing alone (we do not have audio features yet): {", ".join(TONE_TRAITS)}.
C. MESSAGE CLASSIFICATION - classify using one or more of these labels:
   {", ".join(MESSAGE_LABELS)}.
D. CUSTOMER REACTION - based on the customer's actual next response, what
   does it reveal about how they received the statement?
E. SCORE - a score from 1-10 for this exchange, using this rubric:
   9-10: Diagnostic/consultative, clearly customer-focused, creates curiosity
   7-8: Good engagement, mostly customer-focused with minor product-lean
   5-6: Neutral/generic, neither harmful nor especially effective
   3-4: Product-led or salesy, customer showing disengagement
   1-2: Defensive, aggressive, or ignores customer signal entirely
F. BETTER ALTERNATIVE - if the score is below 8, provide one specific
   alternative sentence the salesperson could have said instead. If 8+,
   say "Strong as-is" and explain briefly why.

Respond ONLY with valid JSON in this exact format, no other text:
{{
  "what_was_said": "...",
  "tone_estimate": "...",
  "message_classification": ["..."],
  "customer_reaction": "...",
  "score": 0,
  "explanation": "...",
  "better_alternative": "..."
}}
"""


def build_final_report_prompt(full_journey: list[dict]) -> str:
    """
    Called once at the end of the conversation with every per-turn
    analysis, to produce the overall score and coaching report.
    """
    journey_json = json.dumps(full_journey, indent=2)

    return f"""You are an AI sales conversation coach producing a final report.
Below is the full turn-by-turn analysis of a sales conversation you already
performed.

FULL CONVERSATION ANALYSIS:
{journey_json}

Using ONLY the analysis above (do not invent details not present in it),
produce a final coaching report with:

1. OVERALL SCORE (0-100): average the per-exchange scores, weighted toward
   later exchanges (they show the trend of the conversation), and explain
   briefly how you weighted it.
2. WHAT YOU DID WELL: 3-5 specific examples, quoting or closely paraphrasing
   the actual statements.
3. WHERE YOU LOST THE CUSTOMER: specific statements/moments where score
   dropped or reaction turned negative.
4. WHERE THE CONVERSATION IMPROVED: what specifically caused any positive
   shift.
5. WHAT TO DO DIFFERENTLY: specific alternative sentences (not generic
   advice like "be more consultative").
6. TOP 3 COACHING RECOMMENDATIONS: concrete, actionable, specific to this
   call.

Respond ONLY with valid JSON in this exact format, no other text:
{{
  "overall_score": 0,
  "scoring_explanation": "...",
  "what_you_did_well": ["...", "..."],
  "where_you_lost_the_customer": ["...", "..."],
  "where_it_improved": ["...", "..."],
  "what_to_do_differently": ["...", "..."],
  "top_3_recommendations": ["...", "...", "..."]
}}
"""