"""Collapse dead air (long static spans) in recorded demo videos.

The GE UI takes a median 124s to first answer; that wait is baked into every
recording as a static screen (plus a small spinner). This tool finds static
spans with ffmpeg freezedetect and collapses each long one to a short stub,
so a viewer sees the wait happen without sitting through it.

Deliberate reading dwells (the page-step review holds) are ~5-6s static and
MUST survive: only spans >= MIN_SPAN (10s) are collapsed, and every collapsed
span keeps its first KEEP_HEAD seconds and last KEEP_TAIL seconds.

Usage:
  python scripts/compress_dead_air.py <in.webm> [out.webm]
  python scripts/compress_dead_air.py --batch <dir-with-agent-subdirs> <out-root>

Requires ffmpeg/ffprobe on PATH (installed in ~/.local/bin).
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

FFMPEG = os.path.expanduser("~/.local/bin/ffmpeg")
FFPROBE = os.path.expanduser("~/.local/bin/ffprobe")
NOISE = "0.002"      # freezedetect tolerance: spinner-only frames count as static
MIN_FREEZE_D = 3     # seconds: detector's own minimum
MERGE_GAP = 1.0      # merge freeze segments separated by micro-blips
MIN_SPAN = 10.0      # only collapse spans at least this long (protects dwells)
KEEP_HEAD = 1.2      # seconds of a collapsed span kept at its start
KEEP_TAIL = 0.4      # seconds kept at its end (shows the wait resolving)


def duration_of(path: Path) -> float:
    out = subprocess.run([FFPROBE, "-v", "error", "-show_entries",
                          "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def freeze_spans(path: Path) -> list[tuple[float, float]]:
    p = subprocess.run([FFMPEG, "-hide_banner", "-i", str(path), "-vf",
                        f"freezedetect=n={NOISE}:d={MIN_FREEZE_D}",
                        "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    starts = [float(m) for m in re.findall(r"freeze_start: ([\d.]+)", p.stderr)]
    ends = [float(m) for m in re.findall(r"freeze_end: ([\d.]+)", p.stderr)]
    spans = list(zip(starts, ends))
    if len(starts) == len(ends) + 1:          # video ends frozen
        spans.append((starts[-1], duration_of(path)))
    merged: list[list[float]] = []
    for s, e in spans:
        if merged and s - merged[-1][1] <= MERGE_GAP:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged if e - s >= MIN_SPAN]


def compress(src: Path, dst: Path) -> tuple[float, float]:
    total = duration_of(src)
    cuts = freeze_spans(src)
    if not cuts:
        dst.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["cp", str(src), str(dst)], check=True)
        return total, total
    # keep-intervals = everything outside the collapsed middles
    keeps: list[tuple[float, float]] = []
    cur = 0.0
    for s, e in cuts:
        keeps.append((cur, s + KEEP_HEAD))
        cur = e - KEEP_TAIL
    keeps.append((cur, total))
    keeps = [(a, b) for a, b in keeps if b - a > 0.05]
    parts, chains = [], []
    for i, (a, b) in enumerate(keeps):
        chains.append(f"[0:v]trim=start={a:.2f}:end={b:.2f},"
                      f"setpts=PTS-STARTPTS[v{i}];")
        parts.append(f"[v{i}]")
    graph = "".join(chains) + "".join(parts) + f"concat=n={len(keeps)}:v=1:a=0[out]"
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
                    "-i", str(src), "-filter_complex", graph, "-map", "[out]",
                    "-c:v", "libvpx", "-b:v", "1M", "-deadline", "realtime",
                    "-cpu-used", "8", str(dst)], check=True)
    return total, duration_of(dst)


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] == "--batch":
        root, out_root = Path(args[1]), Path(args[2])
        pairs = []
        for d in sorted(p for p in root.iterdir() if p.is_dir()):
            vids = sorted(d.glob("*.webm"), key=lambda p: p.stat().st_size,
                          reverse=True)
            if vids:
                pairs.append((vids[0], out_root / d.name / vids[0].name))
        for src, dst in pairs:
            t, c = compress(src, dst)
            print(f"  {src.parent.name}: {t:.0f}s -> {c:.0f}s "
                  f"({100 * (1 - c / t):.0f}% cut)", flush=True)
        print(f"BATCH_DONE {len(pairs)} videos")
        return 0
    src = Path(args[0])
    dst = Path(args[1]) if len(args) > 1 else src.with_name(
        src.stem + ".tight.webm")
    t, c = compress(src, dst)
    print(f"{t:.0f}s -> {c:.0f}s ({100 * (1 - c / t):.0f}% cut) -> {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
