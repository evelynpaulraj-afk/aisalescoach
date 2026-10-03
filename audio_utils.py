"""
audio_utils.py
Shared audio decoding used by multiple pipeline stages (diarization,
voice feature extraction). Decodes via the ffmpeg CLI directly rather
than torchcodec, avoiding the Windows DLL loading issues torchcodec has.
"""

import subprocess
import tempfile
import os

import torch
import soundfile as sf


def load_waveform_via_ffmpeg(audio_path: str, target_sr: int = 16000):
    """
    Decodes any audio/video file into a mono, target_sr waveform tensor
    using the ffmpeg CLI. Returns (waveform, sample_rate) where waveform
    has shape (1, num_samples) — the format pyannote expects, and easily
    convertible to numpy for librosa.
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