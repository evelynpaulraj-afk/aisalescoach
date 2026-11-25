"""
diarize.py
Runs speaker diarization with pyannote.audio and merges speaker labels
into the Whisper transcript segments.

Requires a Hugging Face access token, and you must have clicked "Agree"
on the model pages for:
  - https://huggingface.co/pyannote/speaker-diarization-3.1
  - https://huggingface.co/pyannote/segmentation-3.0

NOTE: audio is decoded with PyAV (the ffmpeg libraries that ship inside
faster-whisper's own dependency) rather than letting pyannote/torchaudio use
torchcodec. This avoids the Windows issue where torchcodec can't locate its
DLLs, and means no separate ffmpeg install is needed.

When the speech models are bundled with the desktop app (HF_HUB_OFFLINE=1),
no Hugging Face token is needed at run time.
"""

import json
import os

import av
import numpy as np
import torch
from pyannote.audio import Pipeline

DIARIZED_DIR = "data/diarized"

# Set this via environment variable rather than hardcoding it.
HF_TOKEN = os.environ.get("HF_TOKEN")


def load_waveform(audio_path: str, target_sr: int = 16000):
    """
    Decodes any audio/video file into a mono waveform tensor at target_sr.
    Returns (waveform, sample_rate) where waveform has shape (1, num_samples),
    which is the format pyannote expects.

    Channels are resampled separately and then averaged. (PyAV's built-in mono
    mix uses a different gain; averaging matches the ffmpeg CLI and pyannote's
    own downmix.)
    """
    container = av.open(audio_path)
    try:
        stream = container.streams.audio[0]
        layout = "mono" if stream.channels == 1 else "stereo"
        resampler = av.audio.resampler.AudioResampler(format="fltp", layout=layout, rate=target_sr)
        chunks = []
        for frame in container.decode(stream):
            for out in resampler.resample(frame):
                chunks.append(out.to_ndarray())  # shape (channels, n)
        for out in resampler.resample(None):  # flush
            chunks.append(out.to_ndarray())
    finally:
        container.close()

    if not chunks:
        raise ValueError(f"No audio could be read from {audio_path}")

    mono = np.concatenate(chunks, axis=1).mean(axis=0).astype("float32")
    return torch.from_numpy(mono).unsqueeze(0), target_sr


def run_diarization(audio_path: str) -> list[dict]:
    """
    Returns speaker turn windows:
    [{"start": float, "end": float, "speaker": "SPEAKER_00"}, ...]
    """
    offline = os.environ.get("HF_HUB_OFFLINE") == "1"
    if not HF_TOKEN and not offline:
        raise RuntimeError(
            "HF_TOKEN environment variable not set. "
            "Get a token from huggingface.co/settings/tokens and "
            "export HF_TOKEN=your_token_here"
        )

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        token=HF_TOKEN,
    )

    waveform, sample_rate = load_waveform(audio_path)
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
