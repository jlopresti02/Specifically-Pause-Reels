# Reyes vs Jones: Pause to stop Jones robbing Reyes

Dominick Reyes (mid-jab cutout) sweeps left to right across a space background. A dashed outline
shows where his fist lands on Jon Jones's chin. On one frame per sweep he lines up exactly:
pausing there shows the real photo of Reyes landing on Jones with **POW!**, **ROBBERY STOPPED!**,
a **CAUGHT** stamp and "14 of 21 media members scored UFC 247 for Reyes."

Every other frame is a miss: Jones holds a money bag with the belt sticking out, "THIEF / ROBBED"
scribbles, a red X on Reyes's fist, a taunt like "MISSED. JUST LIKE THE JUDGES." and a Jones
speech bubble ("Missed again? You'd make a great UFC judge."). The taunts change every 4 frames,
so every pause gets a fresh joke.

- 1080x1920, 30fps, 6.0s, 20 frames per sweep (9 chances), 1 hit frame per sweep
- Audio: hamster dance seamless loop sped up ~2.9% (atempo 1.029) so one cycle = one loop

## Files

| Path | What it is |
|---|---|
| `output/reyes-pause-reel-FINAL-big-hamster-dance.mp4` | **The version Joe picked**: big layout, Reyes fully in frame, hamster dance |
| `output/reyes-pause-reel-big-silent.mp4` | Same, no audio |
| `output/reyes-pause-reel-safe-zone-hamster-dance.mp4` | Strict safe-zone layout (fighters ~1/3 smaller), with audio |
| `output/reyes-pause-reel-safe-zone-silent.mp4` | Strict safe-zone layout, no audio |
| `output/big-version-hit-frame.png`, `big-version-miss-frame.png` | Review stills of the big layout |
| `output/hit-frame.png`, `miss-frame-example.png` | Review stills of the safe-zone layout |
| `trial-test/` | 10 trial-reel variants (A to J), `test-plan.md`, `metricool-schedule.md` |
| `assets/` | Source images: space background, Reyes punch cutout, standing Jones, Reyes-hits-Jones photo |
| `render.py` | Renders the reel, the trial variants, or stills |

`render.py` is a rebuild: the first render script lived in a temporary work session and was lost,
so re-renders match the concept, layout and timing but aren't pixel-identical to the posted MP4s.

## Caption

> Only 1% can pause on the exact frame Reyes lands on Jones 🥊 What frame did you get? 👇
>
> 14 of 21 media members scored UFC 247 for Dominick Reyes, but the judges gave the belt to Jon Jones. Robbery or right call?
>
> #ufc #mma #dominickreyes #jonjones #pausegame

## Notes

- The background image has a faint "Slidesdocs" watermark; swap in a clean copy for future reels.
- Trial results: see `trial-test/test-plan.md` (rank by plays, then avg watched %, then skip rate).
