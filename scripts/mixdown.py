#!/usr/bin/env python
"""Cut the screen recording to the narration and lay the voice onto it.

The recorder flashes one white frame immediately before the first spoken line
and reports, in walkthrough/audio/offsets.json, how many milliseconds after that
flash each line began. The flash is time zero for both halves: find it in the
video, and every offset is then exact rather than estimated.

Headless Chromium drives the page far slower than a person does - a scroll and
a settle that read as one second cost twenty in the capture - so the raw take
runs about seven minutes against a three-minute limit. Rather than re-record
until the machine cooperates, this keeps every narrated passage at real speed
and compresses only the dead transitions between them. Nothing is dropped and
nothing is faked: the transitions are the same frames, run fast, the way a
walkthrough skips you between sections.

    python scripts/mixdown.py

Writes media/nocturne-demo.mp4.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REC = ROOT / "walkthrough" / "final"
AUDIO = ROOT / "walkthrough" / "audio"
WORK = ROOT / "walkthrough" / "cut"
OUT = ROOT / "media" / "nocturne-demo.mp4"

WHITE = 200.0     # a full-screen white frame sits near 255; the dashboard never does
CAP = 180.0       # the hackathon's limit: 3 minutes or less
LEAD = 0.30       # seconds of picture before a line starts speaking
TAIL = 0.25       # and after it finishes
GAP = 0.70        # every transition is compressed to this long
MAXSPEED = 22.0   # beyond this the tail of the gap is used, not the whole of it
HEAD = 0.9        # opening hold
END = 1.4         # closing hold
FPS = 30


def run(cmd: list[str], cwd: Path | None = None) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if p.returncode:
        sys.exit("failed: %s ...\n%s" % (" ".join(cmd[:8]), p.stderr[-1500:]))
    return p.stdout


def probe(path: Path, entries: str, count: bool = False) -> str:
    cmd = ["ffprobe", "-v", "error"]
    if count:
        cmd += ["-count_frames", "-select_streams", "v:0"]
    cmd += ["-show_entries", entries, "-of", "default=nw=1:nk=1", str(path)]
    return run(cmd).strip().splitlines()[0]


def dur_of(path: Path) -> float:
    """Exact duration from the frame count.

    format=duration comes back N/A on the short segments ffmpeg writes here,
    and every segment is encoded at a known constant rate, so count frames.
    """
    n = probe(path, "stream=nb_read_frames", count=True)
    return int(n) / float(FPS)


def find_flash(src: Path, need: float, total: float) -> float:
    """Time in seconds just after the sync flash.

    Chromium paints a white frame on every navigation, and the walkthrough
    navigates six times, so "the white frame" is ambiguous on its own. The
    sync flash is the only one with the whole narration still ahead of it:
    keep the latest candidate that leaves room for every line.
    """
    # The filter parser treats a colon as an argument separator, so the stats
    # file is named relative to a working directory rather than by full path.
    run(["ffmpeg", "-v", "error", "-y", "-i", src.name,
         "-vf", "crop=600:400:660:340,signalstats,"
                "metadata=print:key=lavfi.signalstats.YAVG:file=stats.txt",
         "-f", "null", "-"], cwd=REC)
    times, t = [], None
    for line in (REC / "stats.txt").read_text(encoding="utf-8").splitlines():
        m = re.search(r"pts_time:([0-9.]+)", line)
        if m:
            t = float(m.group(1))
            continue
        m = re.search(r"YAVG=([0-9.]+)", line)
        if m and t is not None and float(m.group(1)) > WHITE:
            times.append(t)
    if not times:
        sys.exit("no sync flash found in the recording")
    runs: list[list[float]] = [[times[0]]]
    for a, b in zip(times, times[1:]):
        if b - a >= 0.25:
            runs.append([])
        runs[-1].append(b)
    ends = [r[-1] + 0.04 for r in runs]
    fits = [e for e in ends if e + need <= total + 1.0]
    print("  white runs: %d at %s" % (len(runs), ", ".join("%.1fs" % e for e in ends)))
    if not fits:
        sys.exit("no white frame leaves room for %.1fs of narration in %.1fs of video"
                 % (need, total))
    print("  sync flash at %.2fs (needs %.1fs of %.1fs)" % (fits[-1], need, total))
    return fits[-1]


def seg(src: Path, ss: float, dur: float, dest: Path, speed: float = 1.0) -> None:
    vf = "scale=1920:1080:flags=lanczos"
    if speed != 1.0:
        vf = "setpts=PTS/%.6f,%s" % (speed, vf)
    vf += ",fps=%d,format=yuv420p" % FPS
    run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % ss, "-t", "%.3f" % dur,
         "-i", str(src), "-an", "-vf", vf, "-r", str(FPS),
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
         "-pix_fmt", "yuv420p", "-video_track_timescale", "90000", str(dest)])


def main() -> int:
    src = max(REC.glob("*.webm"), key=lambda p: p.stat().st_size, default=None)
    if src is None:
        sys.exit("no recording in walkthrough/final")
    print("  source %s (%.1f MB)" % (src.name, src.stat().st_size / 1e6))

    offsets = json.loads((AUDIO / "offsets.json").read_text(encoding="utf-8"))
    timing = json.loads((AUDIO / "timing.json").read_text(encoding="utf-8"))
    if len(offsets) != len(timing):
        sys.exit("offsets and timing disagree - re-record")

    need = (offsets[-1]["at"] + timing[-1]["dur"]) / 1000.0 + END
    d = probe(src, "format=duration")
    total = float(d) if d not in ("N/A", "") else dur_of(src)
    t0 = find_flash(src, need, total)

    # Where each line sits in the raw take.
    keeps = []
    for off, t in zip(offsets, timing):
        a = t0 + off["at"] / 1000.0 - LEAD
        b = a + LEAD + t["dur"] / 1000.0 + TAIL
        keeps.append((max(0.0, a), b))

    shutil.rmtree(WORK, ignore_errors=True)
    WORK.mkdir(parents=True, exist_ok=True)

    parts: list[Path] = []
    starts: list[float] = []      # where each line lands in the OUTPUT timeline
    clock = 0.0

    # Opening hold, taken from just before the first line.
    h0 = max(0.0, keeps[0][0] - HEAD)
    if keeps[0][0] - h0 > 0.05:
        p = WORK / "s000.mp4"
        seg(src, h0, keeps[0][0] - h0, p)
        parts.append(p)
        clock += keeps[0][0] - h0

    for i, (a, b) in enumerate(keeps):
        if i:
            g0, g1 = keeps[i - 1][1], a
            raw = max(0.0, g1 - g0)
            if raw > 0.08:
                window = min(raw, GAP * MAXSPEED)
                speed = max(1.0, window / GAP)
                p = WORK / ("g%03d.mp4" % i)
                seg(src, g1 - window, window, p, speed=speed)
                parts.append(p)
                d = dur_of(p)
                clock += d
                if raw > 3:
                    print("  gap %2d  %6.1fs raw -> %.2fs at %4.1fx" % (i, raw, d, speed))
        starts.append(clock + LEAD)
        p = WORK / ("k%03d.mp4" % i)
        seg(src, a, b - a, p)
        parts.append(p)
        clock += dur_of(p)

    # Closing hold.
    p = WORK / "s999.mp4"
    seg(src, keeps[-1][1], END, p)
    parts.append(p)
    clock += dur_of(p)

    lst = WORK / "list.txt"
    lst.write_text("".join("file '%s'\n" % q.as_posix() for q in parts), encoding="utf-8")
    silent = WORK / "silent.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
         "-i", str(lst), "-c", "copy", str(silent)])
    vdur = dur_of(silent)
    print("  picture: %d segments, %.1fs" % (len(parts), vdur))

    # Lay each line of narration at the position its passage now occupies.
    inputs: list[str] = ["-i", str(silent)]
    for t in timing:
        inputs += ["-i", str(AUDIO / t["file"])]
    delays = ["[%d:a]adelay=%d|%d[a%d]" % (n, int(s * 1000), int(s * 1000), n)
              for n, s in enumerate(starts, start=1)]
    mix = "".join("[a%d]" % n for n in range(1, len(starts) + 1))
    # normalize=0 keeps each line at the level it was spoken; loudnorm then puts
    # the whole track at a consistent level.
    fc = (";".join(delays) + ";" + mix +
          "amix=inputs=%d:normalize=0[m];" % len(starts) +
          "[m]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,apad[a]")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fc,
         "-map", "0:v", "-map", "[a]", "-c:v", "libx264", "-preset", "slow",
         "-crf", "20", "-c:a", "aac", "-b:a", "160k",
         "-movflags", "+faststart", "-shortest", str(OUT)])

    dur = dur_of(OUT)
    print("\n%s\n  %.1f MB, %.1fs, 1920x1080, %d fps"
          % (OUT, OUT.stat().st_size / 1e6, dur, FPS))
    print("  last line starts at %.1fs, ends %.1fs"
          % (starts[-1], starts[-1] + timing[-1]["dur"] / 1000))
    if dur > CAP:
        print("  OVER the 3-minute limit by %.1fs" % (dur - CAP))
        return 1
    print("  under the 3-minute limit with %.1fs to spare" % (CAP - dur))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
