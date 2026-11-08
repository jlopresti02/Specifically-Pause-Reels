# Pause game reels

Source, assets and finished renders for the **pause game** reels on the @wwitmma MMA Instagram account.
A pause game is a short looping reel where viewers have to pause on one exact frame to "win"
(for example, freezing a fighter's punch right as it lands).

Kept separate from the ball game repo.

## What works (from past trial reels)

- **~6 seconds, looping.** The top performer (Merab vs Yan cage drop, 316 plays, 108% avg watched) was 6s.
- **20 frames per pass at 30fps, one winning frame per pass.**
- **"CAN YOU …" hooks** did best on screen; captions mattered less.
- Keep text and the main fighter inside the **Instagram safe zone** (x 60–940, y 250–1470 on 1080x1920)
  unless the bigger layout reads better (it did for Reyes).
- Music: the hamster dance loop, time-stretched so one audio cycle = one video loop.
- Don't post a dozen trial copies within minutes; space them about 10 minutes apart.

## Layout

```
pausegame/            shared rendering code
  sweep.py            "cutout sweeps across, pause when it lines up" game
audio/
  hamster-dance-loop/ seamless 6.17s cycle (wav) + 60s mp3
assets/fonts/         drop Bangers + Permanent Marker here (see README inside)
reels/
  reyes-jones/        Pause to stop Jones robbing Reyes
```

Each reel folder has its own `render.py`, `assets/` (source images), `output/` (posted renders
and review stills) and, where relevant, `trial-test/` (A/B variants and the test plan).

## Setup

Videos and images are committed directly (each is a few MB). If the repo grows past ~1 GB,
move media to Git LFS or cloud storage.

```
pip install -r requirements.txt     # Pillow
# also needs ffmpeg on PATH
python reels/reyes-jones/render.py              # main reel
python reels/reyes-jones/render.py --variants   # trial variants A-J
python reels/reyes-jones/render.py --stills     # hit + miss frame PNGs
```

Renders go to `reels/<reel>/renders/` (git-ignored). Copy keepers into `output/`.

## Making a new sweep-style reel

Copy `reels/reyes-jones/` to `reels/<fighter-a>-<fighter-b>/`, swap the four images in `assets/`
(background, mover cutout, standing opponent, payoff photo), and edit the headline, taunts and
trash talk in `render.py`. Layout knobs (scales, positions, frames per sweep, contrast) are fields
on `SweepReel` in `pausegame/sweep.py`.
