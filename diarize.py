"""
diarize.py
Runs speaker diarization with pyannote.audio and merges speaker labels
into the Whisper transcript segments.

Requires a Hugging Face access token, and you must have clicked "Agree"
on the model pages for:
  - https://huggingface.co/pyannote/speaker-diarization-3.1
  - https://huggingface.co/pyannote/segmentation-3.0

NOTE: audio is decoded manually via the ffmpeg command-line tool rather
than letting pyannote/torchaudio use torchcodec. This avoids a common
Windows issue where torchcodec can't locate its DLLs even when FFmpeg
is correctly installed and on PATH.
"""

import json
import os
import subprocess
import tempfile
from dotenv import load_dotenv
load_dotenv()
import torch
import soundfile as sf
from pyannote.audio import Pipeline

DIARIZED_DIR = "data/diarized"

# Set this via environment variable rather than hardcoding it.
HF_TOKEN = os.environ.get("HF_TOKEN")


def load_waveform_via_ffmpeg(audio_path: str, target_sr: int = 16000):
    """
    Decodes any audio/video file into a mono, 16kHz waveform tensor using
    the ffmpeg CLI directly (bypassing torchcodec entirely).
    Returns (waveform, sample_rate) where waveform has shape (1, num_samples),
    which is the format pyannote expects.
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_wav_path = tmp.name

    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", audio_path,
                "-ac", "1", "-ar", str(target_sr),
                tmp_wav_path,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        data, sr = sf.read(tmp_wav_path, dtype="float32")
        waveform = torch.from_numpy(data).unsqueeze(0)  # shape (1, num_samples)
        return waveform, sr
    finally:
        os.remove(tmp_wav_path)


def run_diarization(audio_path: str) -> list[dict]:
    """
    Returns speaker turn windows:
    [{"start": float, "end": float, "speaker": "SPEAKER_00"}, ...]
    """
    if not HF_TOKEN:
        raise RuntimeError(
            "HF_TOKEN environment variable not set. "
            "Get a token from huggingface.co/settings/tokens and "
            "export HF_TOKEN=your_token_here"
        )

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        token=HF_TOKEN,
    )

    waveform, sample_rate = load_waveform_via_ffmpeg(audio_path)
    diarization = pipeline({"waveform": waveform, "sample_rate": sample_rate})

    speaker_segments = []
    for turn, speaker in diarization.speaker_diarization:
        speaker_segments.append({
            "start": round(turn.start, 2),
            "end": round(turn.end, 2),
            "speaker": speaker,
        })
    return speaker_segments


def assign_speaker(whisper_seg: dict, speaker_segments: list[dict]) -> str:
    """
    Assigns a Whisper segment to whichever diarized speaker window
    overlaps it the most.
    """
    best_overlap, best_speaker = 0, "UNKNOWN"
    for sp in speaker_segments:
        overlap = min(whisper_seg["end"], sp["end"]) - max(whisper_seg["start"], sp["start"])
        if overlap > best_overlap:
            best_overlap, best_speaker = overlap, sp["speaker"]
    return best_speaker


def merge_transcript_with_speakers(transcript: list[dict], speaker_segments: list[dict]) -> list[dict]:
    """
    Adds a "speaker" field (e.g. "SPEAKER_00") to each transcript segment.
    """
    for seg in transcript:
        seg["speaker"] = assign_speaker(seg, speaker_segments)
    return transcript


def diarize_and_cache(audio_path: str, transcript: list[dict]) -> list[dict]:
    """
    Runs diarization (or loads cache) and merges speaker labels into transcript.
    """
    os.makedirs(DIARIZED_DIR, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    cache_path = os.path.join(DIARIZED_DIR, f"{base_name}.json")

    if os.path.exists(cache_path):
        print(f"[diarize] Loading cached diarized transcript: {cache_path}")
        with open(cache_path, "r") as f:
            return json.load(f)

    print(f"[diarize] Running pyannote on {audio_path} ...")
    speaker_segments = run_diarization(audio_path)
    merged = merge_transcript_with_speakers(transcript, speaker_segments)

    with open(cache_path, "w") as f:
        json.dump(merged, f, indent=2)
    print(f"[diarize] Saved diarized transcript: {cache_path}")

    return merged


if __name__ == "__main__":
    # Quick standalone test: python diarize.py path/to/audio.mp3 path/to/transcript.json
    import sys
    if len(sys.argv) < 3:
        print("Usage: python diarize.py <audio_file> <transcript_json>")
        sys.exit(1)

    with open(sys.argv[2], "r") as f:
        transcript = json.load(f)

    merged = diarize_and_cache(sys.argv[1], transcript)
    for s in merged:
        print(f"[{s['start']:.2f}-{s['end']:.2f}] {s['speaker']}: {s['text']}")