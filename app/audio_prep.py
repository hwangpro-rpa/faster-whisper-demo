"""Light audio cleanup before handing samples to Whisper.

Just peak normalization. Spectral noise reduction (noisereduce) was tried
here and measured *worse* on short clips: with nothing but clean signal to
work with, it subtracts part of the actual voice energy and Whisper
hallucinates on what's left (e.g. a clean 0.6s "light" recording came out
as "Thank you for watching and see you in the next video." after
noise-reduction, vs. correctly as "LIGHT" with normalization alone). Don't
reintroduce it without re-testing against real noisy recordings first.
"""

import numpy as np
from faster_whisper.audio import decode_audio

SAMPLE_RATE = 16000


def load_and_clean_audio(path: str) -> np.ndarray:
    audio = decode_audio(path, sampling_rate=SAMPLE_RATE)

    peak = float(np.abs(audio).max()) if audio.size else 0.0
    if peak > 1e-4:
        audio = audio / peak * 0.95

    return audio.astype(np.float32)
