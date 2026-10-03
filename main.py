"""
main.py
Runs the full pipeline: transcribe -> diarize -> analyze -> report.

Usage:
    python main.py path/to/sales_call.mp3
"""

import sys
import json

from transcribe import transcribe_and_cache
from diarize import diarize_and_cache
from analyze import analyze_and_cache


def run_pipeline(audio_path: str):
    print(f"\n=== Processing: {audio_path} ===\n")

    print("Step 1/3: Transcribing...")
    transcript = transcribe_and_cache(audio_path)

    print("\nStep 2/3: Diarizing (identifying speakers)...")
    diarized = diarize_and_cache(audio_path, transcript)

    print("\nStep 3/3: Analyzing conversation...")
    result = analyze_and_cache(audio_path, diarized)

    print("\n=== FINAL REPORT ===\n")
    print(json.dumps(result["final_report"], indent=2))

    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <audio_file>")
        sys.exit(1)

    run_pipeline(sys.argv[1])