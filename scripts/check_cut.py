#!/usr/bin/env python
"""Pull one frame from the middle of every narrated line in the finished video.

This is how the cut gets checked rather than assumed. A take where the page
never scrolled still produced a perfectly valid three-minute file - the only
way to know was to look at what was on screen while each line was spoken.

Positions come from the cut itself: walkthrough/cut/list.txt is the exact
concat order, so accumulating the segment durations gives the start of every
k-segment, and a k-segment is one spoken line.

    python scripts/check_cut.py           -> scratch/vid/chk/NN_tag.png

Writes walkthrough/cut/manifest.json too, if the mixdown did not.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "walkthrough" / "cut"
AUDIO = ROOT / "walkthrough" / "audio"
VIDEO = ROOT / "media" / "nocturne-demo.mp4"
SHOTS = ROOT / "scratch" / "vid" / "chk"
LEAD = 0.30
FPS = 30


def run(cmd: list[str]) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode:
        sys.exit("failed: %s\n%s" % (" ".join(cmd[:6]), p.stderr[-800:]))
    return p.stdout


def dur_of(path: Path) -> float:
    n = run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
             "-show_entries", "stream=nb_read_frames",
             "-of", "default=nw=1:nk=1", str(path)]).strip().splitlines()[0]
    return int(n) / float(FPS)


def main() -> int:
    lst = WORK / "list.txt"
    if not lst.exists():
        sys.exit("no cut in walkthrough/cut - run scripts/mixdown.py first")
    timing = json.loads((AUDIO / "timing.json").read_text(encoding="utf-8"))

    clock, starts = 0.0, []
    for line in lst.read_text(encoding="utf-8").splitlines():
        m = re.match(r"file '(.+)'", line.strip())
        if not m:
            continue
        p = Path(m.group(1))
        if not p.is_absolute():
            p = WORK / p.name
        if p.name.startswith("k"):
            starts.append(clock + LEAD)
        clock += dur_of(p)

    if len(starts) != len(timing):
        sys.exit("cut has %d lines, narration has %d" % (len(starts), len(timing)))

    rows = [{"i": t["i"], "tag": t["tag"], "start": round(st, 2),
             "end": round(st + t["dur"] / 1000.0, 2), "line": t["line"]}
            for t, st in zip(timing, starts)]
    (WORK / "manifest.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")

    SHOTS.mkdir(parents=True, exist_ok=True)
    for f in SHOTS.glob("*.png"):
        f.unlink()
    for r in rows:
        at = (r["start"] + r["end"]) / 2
        out = SHOTS / ("%02d_%s.png" % (r["i"], r["tag"].replace(" ", "-")))
        run(["ffmpeg", "-v", "error", "-y", "-ss", "%.2f" % at,
             "-i", str(VIDEO), "-frames:v", "1", str(out)])
        print("  %2d  %6.1fs  %-20s %s" % (r["i"], at, r["tag"], out.name))
    print("\n%d frames in %s" % (len(rows), SHOTS))
    print("total picture %.1fs" % clock)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
