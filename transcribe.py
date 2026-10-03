"""
transcribe.py
Converts an audio file into timestamped text segments using faster-whisper.
Caches output to data/transcripts/<name>.json so you don't re-run Whisper
every time you tweak downstream code.
"""

import json
import os
from faster_whisper import WhisperModel

TRANSCRIPTS_DIR = "data/transcripts"


def transcribe_audio(audio_path: str, model_size: str = "base") -> list[dict]:
    """
    Runs Whisper on audio_path and returns a list of segments:
    [{"start": float, "end": float, "text": str}, ...]
    """
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, info = model.transcribe(audio_path, word_timestamps=True)

    result = []
    for seg in segments:
        result.append({
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": seg.text.strip(),
        })
    return result


def transcribe_and_cache(audio_path: str, model_size: str = "base") -> list[dict]:
    """
    Transcribes audio_path, or loads a cached transcript if one already
    exists for this filename.
    """
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    cache_path = os.path.join(TRANSCRIPTS_DIR, f"{base_name}.json")

    if os.path.exists(cache_path):
        print(f"[transcribe] Loading cached transcript: {cache_path}")
        with open(cache_path, "r") as f:
            return json.load(f)

    print(f"[transcribe] Running Whisper on {audio_path} ...")
    segments = transcribe_audio(audio_path, model_size=model_size)

    with open(cache_path, "w") as f:
        json.dump(segments, f, indent=2)
    print(f"[transcribe] Saved transcript: {cache_path}")

    return segments


if __name__ == "__main__":
    # Quick standalone test: python transcribe.py path/to/audio.mp3
    import sys
    if len(sys.argv) < 2:
        print("Usage: python transcribe.py <audio_file>")
        sys.exit(1)

    segs = transcribe_and_cache(sys.argv[1])
    for s in segs:
        print(f"[{s['start']:.2f}-{s['end']:.2f}] {s['text']}")