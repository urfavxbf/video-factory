"""Create an original, royalty-free-to-us synthesized ambient instrumental loop."""
from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

SAMPLE_RATE = 22050
DURATION = 24
CHORDS = (
    (220.0, 261.63, 329.63),  # Am
    (174.61, 220.0, 261.63),  # F
    (196.0, 261.63, 329.63),  # C-ish inversion
    (196.0, 246.94, 293.66), # G
)

def generate_music(target: Path) -> Path:
    """Synthesize an original soft pad, arpeggio and pulse. No external copyrighted samples."""
    target.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(target), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        # Write bounded blocks to avoid retaining large audio buffers in memory.
        for start in range(0, SAMPLE_RATE * DURATION, 4096):
            data = bytearray()
            stop = min(start + 4096, SAMPLE_RATE * DURATION)
            for i in range(start, stop):
                t = i / SAMPLE_RATE
                chord = CHORDS[min(int(t // 6), 3)]
                section_t = t % 6.0
                fade = min(1.0, t / 1.1, (DURATION - t) / 1.5)
                pad = sum(
                    math.sin(2 * math.pi * f * t) * (0.7 + 0.2 * math.sin(2 * math.pi * 0.17 * t))
                    for f in chord
                ) / 3
                arp_t = t % 0.75
                arp_f = chord[int(t / 0.75) % 3] * 2
                arp = math.sin(2 * math.pi * arp_f * arp_t) * math.exp(-6 * arp_t)
                pulse_t = t % 1.5
                pulse = math.sin(2 * math.pi * (67 - 16 * pulse_t) * pulse_t) * math.exp(-10 * pulse_t)
                value = max(-0.9, min(0.9, fade * (0.27 * pad + 0.10 * arp + 0.09 * pulse)))
                data.extend(struct.pack("<h", int(value * 32767)))
            wav.writeframesraw(data)
    return target
