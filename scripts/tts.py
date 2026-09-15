#!/usr/bin/env python
"""Speak the walkthrough script, and record exactly when each word is said.

The caption in the video lights one word at a time. If that highlight runs off
an assumed reading speed it drifts against the voice within a couple of
sentences, which is worse than no caption at all. So the voice is synthesised
first and we ask the synthesiser where every word actually lands; the recorder
plays the highlight from those marks and reports back where each line started,
and the mixdown drops each line of audio at exactly that offset.

    python scripts/tts.py --voice en-US-AndrewNeural

Writes walkthrough/audio/NN.mp3 and walkthrough/audio/timing.json.

Needs edge-tts. It is a build-time dependency only; nothing in the running
product imports it.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "walkthrough" / "script.json"
OUT = ROOT / "walkthrough" / "audio"


def duration_ms(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out) * 1000.0


async def speak(text: str, voice: str, rate: str, dest: Path) -> list[dict]:
    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    words: list[dict] = []
    with dest.open("wb") as fh:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                fh.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # edge-tts reports in 100-nanosecond ticks
                words.append({"text": chunk["text"],
                              "at": chunk["offset"] / 10_000.0,
                              "dur": chunk["duration"] / 10_000.0})
    return words


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="en-US-AndrewNeural")
    ap.add_argument("--rate", default="+6%")
    args = ap.parse_args()

    lines = json.loads(SCRIPT.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)

    timing, total = [], 0.0
    for i, item in enumerate(lines):
        dest = OUT / f"{i:02d}.mp3"
        words = await speak(item["line"], args.voice, args.rate, dest)
        dur = duration_ms(dest)
        total += dur
        timing.append({"i": i, "tag": item["tag"], "line": item["line"],
                       "file": dest.name, "dur": round(dur, 1),
                       "words": [{"text": w["text"], "at": round(w["at"], 1)} for w in words]})
        print(f"  {i:02d} {item['tag']:<20} {dur/1000:6.2f}s  {len(words):3d} words")

    (OUT / "timing.json").write_text(json.dumps(timing, indent=1), encoding="utf-8")
    words_total = sum(len(t["words"]) for t in timing)
    print(f"\nvoice {args.voice} at {args.rate}")
    print(f"speech {total/1000:.1f}s over {len(lines)} lines, {words_total} words")
    if total / 1000 > 165:
        print("  WARNING: speech alone leaves no room under the 3-minute cap")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
