"""Reyes vs Jones: "Pause to stop Jones robbing Reyes".

Usage (from the repo root):
    python reels/reyes-jones/render.py                 # main reel (big layout + hamster dance)
    python reels/reyes-jones/render.py --variants      # the 10 trial-reel variants A-J
    python reels/reyes-jones/render.py --stills        # a hit frame and a miss frame PNG
    python reels/reyes-jones/render.py --out-dir /tmp/x  # write somewhere else

The committed MP4s in output/ and trial-test/ are the ones that were posted.
This script is a rebuild of the original (the first render script lived in a
temporary session and was lost), so a re-render matches the layout and timing
but will not be pixel-identical.
"""
from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from pausegame.sweep import SweepReel, render, still  # noqa: E402

A = HERE / "assets"

TAUNTS = [
    "MISSED. JUST LIKE THE JUDGES.",
    "YOU SCORED IT FOR JONES TOO?",
    "THAT'S A 48-47 FOR THE THIEF",
    "EVEN THE JUDGES WOULD'VE HIT THAT",
    "ROBBED AGAIN. UFC 247 ENERGY.",
    "14 MEDIA MEMBERS ARE DISAPPOINTED",
    "TOO SLOW. JONES KEEPS THE BELT.",
    "YOU HAD ONE FRAME. ONE.",
]

TRASH_TALK = [
    "Can't touch me. Ask the judges.",
    "Missed again? You'd make a great UFC judge.",
    "This belt looks better on me anyway.",
    "Same result as 2020.",
    "Bones don't get hit. Bones get decisions.",
    "Try again. I'll still be champ.",
]


def base(out: Path) -> SweepReel:
    return SweepReel(
        background=A / "background-space.jpg",
        mover=A / "reyes-punch.png",
        target=A / "jones-standing.jpg",
        hit_image=A / "reyes-hits-jones.png",
        headline=["PAUSE TO STOP", "JONES ROBBING REYES"],
        out=out,
        frames_per_sweep=20,          # matches the top Merab vs Yan pause game
        duration=6.0,
        taunts=TAUNTS,
        trash_talk=TRASH_TALK,
        hit_lines=["ROBBERY STOPPED!"],
        hit_sub="JUSTICE FOR REYES. 14 of 21 media members scored UFC 247 for Reyes.",
        audio_loop=REPO / "audio" / "hamster-dance-loop" / "hamster-dance-loop-seamless.wav",
    )


# Trial-reel variants. A-F change one thing from the control; G-J add the
# high-contrast look to each variable.
VARIANTS = {
    "A-control": {},
    "B-fast": {"frames_per_sweep": 15},
    "C-slow": {"frames_per_sweep": 30},
    "D-can-you": {"headline": ["CAN YOU STOP", "JONES ROBBING REYES?"]},
    "E-contrast": {"contrast": True},
    "F-only-1pct": {"headline": ["ONLY 1% CAN STOP", "JONES ROBBING REYES"]},
    "G-contrast-fast": {"contrast": True, "frames_per_sweep": 15},
    "H-contrast-slow": {"contrast": True, "frames_per_sweep": 30},
    "I-contrast-can-you": {"contrast": True, "headline": ["CAN YOU STOP", "JONES ROBBING REYES?"]},
    "J-contrast-only-1pct": {"contrast": True, "headline": ["ONLY 1% CAN STOP", "JONES ROBBING REYES"]},
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", action="store_true")
    ap.add_argument("--stills", action="store_true")
    ap.add_argument("--silent", action="store_true", help="no audio")
    ap.add_argument("--out-dir", type=Path, default=HERE / "renders")
    a = ap.parse_args()

    if a.stills:
        cfg = base(a.out_dir / "x.mp4")
        hit = cfg.hit_index if cfg.hit_index is not None else round(cfg.frames_per_sweep * 0.4)
        print(still(cfg, hit, a.out_dir / "hit-frame.png"))
        print(still(cfg, 2, a.out_dir / "miss-frame.png"))
        return

    jobs = {"reyes-pause-reel": {}} if not a.variants else {f"reyes-trial-{k}": v for k, v in VARIANTS.items()}
    for name, overrides in jobs.items():
        cfg = base(a.out_dir / f"{name}.mp4")
        for key, val in overrides.items():
            setattr(cfg, key, copy.deepcopy(val))
        if a.silent:
            cfg.audio_loop = None
        print(render(cfg))


if __name__ == "__main__":
    main()
