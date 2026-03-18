"""Terminal beep-based sound effects.

Uses terminal bell and curses.beep/flash for audio feedback.
Optional: if the `simpleaudio` package is installed, plays short
synthesized tones for a richer experience.
"""

from __future__ import annotations

import curses
import math
import struct
import wave
from io import BytesIO
from typing import TYPE_CHECKING

_sa = None
try:
    import simpleaudio as sa  # type: ignore[import-untyped]

    _sa = sa
except ImportError:
    pass


def _generate_tone(frequency: float, duration_ms: int, volume: float = 0.3) -> bytes:
    """Generate a raw PCM tone."""
    sample_rate = 22050
    num_samples = int(sample_rate * duration_ms / 1000)
    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        # Simple sine with decay envelope
        envelope = max(0.0, 1.0 - (i / num_samples) * 0.5)
        value = volume * envelope * math.sin(2 * math.pi * frequency * t)
        samples.append(int(value * 32767))

    buf = BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return buf.getvalue()


class SoundEngine:
    """Manages game sound effects."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled and _sa is not None
        self._cache: dict[str, object] = {}

    def play(self, event: str) -> None:
        """Play a sound for a game event."""
        if not self.enabled:
            return

        if event not in self._cache:
            tone = self._get_tone(event)
            if tone is None:
                return
            try:
                self._cache[event] = _sa.WaveObject.from_wave_file(BytesIO(tone))  # type: ignore[union-attr]
            except Exception:
                return

        try:
            self._cache[event].play()  # type: ignore[union-attr]
        except Exception:
            pass

    def beep(self) -> None:
        """Simple terminal beep fallback."""
        try:
            curses.beep()
        except curses.error:
            pass

    def _get_tone(self, event: str) -> bytes | None:
        """Get tone parameters for an event."""
        tones: dict[str, tuple[float, int]] = {
            "dot": (880, 30),
            "pellet": (440, 100),
            "eat_ghost": (660, 80),
            "death": (220, 300),
            "won": (880, 200),
            "extra_life": (1047, 150),
            "start": (523, 100),
        }
        params = tones.get(event)
        if params:
            return _generate_tone(params[0], params[1])
        return None
