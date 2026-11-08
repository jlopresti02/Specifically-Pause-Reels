"""Cutout-sweep pause game renderer.

A fighter cutout sweeps left to right across a 1080x1920 frame. A dashed
outline shows where he needs to be. On exactly one frame per sweep the cutout
sits inside the outline: that is the "hit" frame, which swaps in a payoff
image and celebration text. Every other frame is a "miss" frame with taunts
that change every few frames, so wherever a viewer pauses they get a fresh joke.

The reel is rendered to PNG frames with Pillow, then encoded with ffmpeg. An
optional audio loop is time-stretched so one audio cycle equals one video loop.
"""
from __future__ import annotations

import math
import random
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

W, H = 1080, 1920
FPS = 30
REPO = Path(__file__).resolve().parent.parent
FONT_DIR = REPO / "assets" / "fonts"

# Instagram Reels safe zone on 1080x1920 (clear of top bar, caption, action rail).
SAFE_ZONE = (60, 250, 940, 1470)


# --------------------------------------------------------------------------- fonts
def font(kind: str, size: int) -> ImageFont.FreeTypeFont:
    """kind = 'headline' (Bangers) or 'marker' (Permanent Marker).

    Drop the Google Fonts TTFs into assets/fonts/ to match the published reels.
    Falls back to system bold fonts so the script always runs.
    """
    wanted = {
        "headline": ["Bangers-Regular.ttf", "Anton-Regular.ttf"],
        "marker": ["PermanentMarker-Regular.ttf", "Kalam-Bold.ttf"],
    }[kind]
    fallbacks = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    for name in wanted:
        p = FONT_DIR / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    for p in fallbacks:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


# --------------------------------------------------------------------------- images
def load_cutout(path: Path, white_key: bool | None = None) -> Image.Image:
    """Load an image as RGBA. JPEG/RGB images on a white background get the
    background keyed out (flood fill from the border, so white inside the
    fighter, like gloves or logos, is kept)."""
    im = Image.open(path)
    if im.mode == "RGBA" and white_key is not True:
        return im
    im = im.convert("RGB")
    near_white = im.convert("L").point(lambda v: 255 if v > 232 else 0)
    mask = near_white.copy()
    w, h = mask.size
    for x in range(0, w, 8):
        for y in (0, h - 1):
            if mask.getpixel((x, y)) == 255:
                ImageDraw.floodfill(mask, (x, y), 128)
    for y in range(0, h, 8):
        for x in (0, w - 1):
            if mask.getpixel((x, y)) == 255:
                ImageDraw.floodfill(mask, (x, y), 128)
    alpha = mask.point(lambda v: 0 if v == 128 else 255)
    alpha = alpha.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1))
    out = im.convert("RGBA")
    out.putalpha(alpha)
    return out.crop(out.getbbox())


def cover(im: Image.Image, size=(W, H)) -> Image.Image:
    """Scale and centre-crop to fill the frame."""
    sw, sh = size
    s = max(sw / im.width, sh / im.height)
    im = im.resize((math.ceil(im.width * s), math.ceil(im.height * s)), Image.LANCZOS)
    l, t = (im.width - sw) // 2, (im.height - sh) // 2
    return im.crop((l, t, l + sw, t + sh)).convert("RGBA")


def scaled(im: Image.Image, scale: float) -> Image.Image:
    return im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)


def fist_point(cutout: Image.Image) -> tuple[int, int]:
    """Rightmost opaque point of a cutout: the punching fist for a right-facing jab."""
    a = cutout.getchannel("A")
    bbox = a.getbbox()
    x = bbox[2] - 1
    col = [y for y in range(a.height) if a.getpixel((x - 2, y)) > 128]
    y = col[len(col) // 2] if col else a.height // 2
    return x, y


# --------------------------------------------------------------------------- drawing
def text_block(draw, xy, lines, fnt, fill, stroke=8, stroke_fill="black", spacing=6, anchor="mt"):
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=fnt, fill=fill, stroke_width=stroke,
                  stroke_fill=stroke_fill, anchor=anchor)
        bb = draw.textbbox((x, y), line, font=fnt, stroke_width=stroke, anchor=anchor)
        y = bb[3] + spacing
    return y


def fit(draw, lines, fnt, max_w, stroke=8):
    """Shrink a font until every line fits max_w (keeps headlines inside the frame)."""
    size = fnt.size
    while size > 20:
        if all(draw.textlength(l, font=fnt) + 2 * stroke <= max_w for l in lines):
            return fnt
        size -= 4
        fnt = fnt.font_variant(size=size)
    return fnt


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if draw.textlength(t, font=fnt) <= max_w or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def dashed_outline(cutout: Image.Image, color=(255, 255, 255), fill_alpha=70, dash=26) -> Image.Image:
    """Ghost silhouette with a dashed edge, the 'he goes here' target."""
    a = cutout.getchannel("A").point(lambda v: 255 if v > 100 else 0)
    edge = ImageChops.subtract(a.filter(ImageFilter.MaxFilter(9)), a.filter(ImageFilter.MinFilter(3)))
    # break the edge into dashes with a diagonal stripe mask
    stripes = Image.new("L", a.size, 0)
    sd = ImageDraw.Draw(stripes)
    for k in range(-a.height, a.width, dash * 2):
        sd.polygon([(k, 0), (k + dash, 0), (k + dash + a.height, a.height), (k + a.height, a.height)], fill=255)
    edge = ImageChops.multiply(edge, stripes)
    out = Image.new("RGBA", a.size, color + (0,))
    out.putalpha(a.point(lambda v: fill_alpha if v else 0))
    line = Image.new("RGBA", a.size, color + (255,))
    line.putalpha(edge)
    return Image.alpha_composite(out, line)


def speech_bubble(draw, box, text, fnt, tail_to):
    x0, y0, x1, y1 = box
    tx, ty = tail_to
    draw.polygon([(tx - 40, y1 - 4), (tx + 40, y1 - 4), (tx, ty)], fill="white", outline="black")
    draw.rounded_rectangle(box, radius=34, fill="white", outline="black", width=6)
    draw.line([(tx - 37, y1 - 3), (tx + 37, y1 - 3)], fill="white", width=6)
    lines = wrap(draw, text, fnt, x1 - x0 - 60)
    lh = fnt.size + 10
    y = (y0 + y1) / 2 - lh * len(lines) / 2 + 4
    for ln in lines:
        draw.text(((x0 + x1) / 2, y), ln, font=fnt, fill="black", anchor="mt")
        y += lh


def money_bag(size=200) -> Image.Image:
    im = Image.new("RGBA", (size, int(size * 1.45)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    s = size
    # belt sticking out of the bag
    d.rounded_rectangle((s * 0.02, s * 0.06, s * 0.98, s * 0.24), radius=12, fill=(214, 175, 55), outline="black", width=5)
    d.ellipse((s * 0.33, 0, s * 0.67, s * 0.32), fill=(230, 190, 60), outline="black", width=5)
    d.text((s * 0.5, s * 0.16), "UFC", font=font("headline", int(s * 0.14)), fill="black", anchor="mm")
    d.polygon([(s * 0.36, s * 0.42), (s * 0.64, s * 0.42), (s * 0.56, s * 0.3), (s * 0.44, s * 0.3)], fill=(205, 170, 100), outline="black")
    d.rectangle((s * 0.3, s * 0.4, s * 0.7, s * 0.44), fill=(60, 40, 20))
    d.ellipse((0, s * 0.42, s, s * 1.42), fill=(205, 170, 100), outline="black", width=6)
    d.text((s * 0.5, s * 0.93), "$", font=font("headline", int(s * 0.62)), fill=(30, 140, 50),
           stroke_width=5, stroke_fill="black", anchor="mm")
    return im


def scribble(text, fnt, color=(235, 40, 40), angle=-12) -> Image.Image:
    tmp = Image.new("RGBA", (int(fnt.size * len(text) * 0.9) + 40, fnt.size * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    d.text((20, fnt.size // 2), text, font=fnt, fill=color, stroke_width=4, stroke_fill="black")
    tmp = tmp.crop(tmp.getbbox())
    return tmp.rotate(angle, expand=True, resample=Image.BICUBIC)


def stamp(text, fnt, color=(220, 30, 30), angle=-14) -> Image.Image:
    d0 = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bb = d0.textbbox((0, 0), text, font=fnt)
    pad = 26
    im = Image.new("RGBA", (bb[2] - bb[0] + pad * 2, bb[3] - bb[1] + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((4, 4, im.width - 5, im.height - 5), radius=14, outline=color, width=10)
    d.text((im.width / 2, im.height / 2), text, font=fnt, fill=color, anchor="mm")
    return im.rotate(angle, expand=True, resample=Image.BICUBIC)


# --------------------------------------------------------------------------- config
@dataclass
class SweepReel:
    background: Path
    mover: Path              # cutout that sweeps (Reyes mid-punch)
    target: Path             # standing opponent (Jones)
    hit_image: Path          # payoff photo shown on the hit frame
    headline: list[str]      # two lines: [white line, coloured line]
    out: Path

    frames_per_sweep: int = 20
    duration: float = 6.0
    hit_index: int | None = None     # frame within each sweep that lines up (default ~40%)

    # layout ("big" layout Joe picked: fighters large, Reyes fully in frame from the left)
    mover_scale: float = 0.60
    target_height: int = 860
    target_x: int = 812              # left edge of the standing opponent
    ground_y: int = 1800             # bottom of the opponent's feet
    outline_left: int = 20           # left edge of the outline / lined-up mover
    headline_y: int = 250

    # look
    contrast: bool = False           # darker background + yellow/cyan headline
    headline_colors: tuple = ((255, 255, 255), (238, 58, 58))
    contrast_colors: tuple = ((255, 228, 40), (40, 230, 255))

    # copy
    taunts: list[str] = field(default_factory=list)
    trash_talk: list[str] = field(default_factory=list)
    scribbles: list[str] = field(default_factory=lambda: ["THIEF", "ROBBED"])
    hit_lines: list[str] = field(default_factory=lambda: ["ROBBERY STOPPED!"])
    hit_sub: str = ""
    hit_stamp: str = "CAUGHT"
    target_hint: str = "HE GOES HERE"
    change_every: int = 4            # frames between taunt changes

    audio_loop: Path | None = None   # one seamless cycle (wav)
    seed: int = 7


# --------------------------------------------------------------------------- render
def render(cfg: SweepReel, frames_only: Path | None = None) -> Path:
    rnd = random.Random(cfg.seed)
    total = round(cfg.duration * FPS)
    n = cfg.frames_per_sweep
    hit_i = cfg.hit_index if cfg.hit_index is not None else round(n * 0.4)

    bg = cover(Image.open(cfg.background))
    if cfg.contrast:
        bg = ImageEnhance.Brightness(bg).enhance(0.55)
        bg = ImageEnhance.Contrast(bg).enhance(1.25)
    head_cols = cfg.contrast_colors if cfg.contrast else cfg.headline_colors

    mover = scaled(load_cutout(cfg.mover), cfg.mover_scale)
    target = load_cutout(cfg.target)
    target = scaled(target, cfg.target_height / target.height)
    tpos = (cfg.target_x, cfg.ground_y - target.height)

    fx, fy = fist_point(mover)
    # line the fist up with the opponent's chin (about 13% down his body)
    chin = (tpos[0] + int(target.width * 0.42), tpos[1] + int(target.height * 0.11))
    lined_up = (cfg.outline_left, chin[1] - fy)
    # stretch so the mover's fist reaches the chin when its left edge sits at outline_left
    if cfg.outline_left + fx != chin[0]:
        s = (chin[0] - cfg.outline_left) / fx
        mover = scaled(mover, s)
        fx, fy = fist_point(mover)
        lined_up = (cfg.outline_left, chin[1] - fy)
    ghost = dashed_outline(mover)

    # sweep path: x moves linearly; frame hit_i lands exactly on lined_up[0]
    start_x, end_x = -mover.width - 40, W + 40
    step = (end_x - start_x) / (n - 1)
    start_x = lined_up[0] - hit_i * step

    hit_img = load_cutout(cfg.hit_image)
    hit_img = scaled(hit_img, (W - 2 * 10) / hit_img.width)
    hit_pos = (10, chin[1] - int(hit_img.height * 0.32))

    f_head = font("headline", 118)
    f_taunt = font("marker", 66)
    f_bubble = font("marker", 42)
    f_scrib = font("marker", 54)
    f_hint = font("marker", 56)
    f_hit = font("headline", 140)
    f_stamp = font("headline", 120)
    f_sub = font("marker", 46)

    bag = money_bag(190)
    scribs = [scribble(t, f_scrib, angle=rnd.choice([-14, -8, 10])) for t in cfg.scribbles]
    taunts = cfg.taunts or ["MISSED."]
    talk = cfg.trash_talk or ["Can't touch me."]

    tmp = Path(frames_only) if frames_only else Path(tempfile.mkdtemp(prefix="pausegame_"))
    tmp.mkdir(parents=True, exist_ok=True)

    for i in range(total):
        k = i % n
        hit = k == hit_i
        fr = bg.copy()
        d = ImageDraw.Draw(fr)

        if hit:
            glow = dashed_outline(mover, color=(255, 205, 40), fill_alpha=40)
            fr.alpha_composite(glow, lined_up)
            fr.alpha_composite(hit_img, hit_pos)
            d = ImageDraw.Draw(fr)
            pow_ = stamp("POW!", f_head, color=(255, 215, 0), angle=12)
            px = min(chin[0] - pow_.width // 2, W - pow_.width - 20)
            fr.alpha_composite(pow_, (px, chin[1] - pow_.height - 60))
            y = text_block(d, (W // 2, 560), cfg.hit_lines, fit(d, cfg.hit_lines, f_hit, W - 120, 10),
                           (255, 215, 0), stroke=10)
            st = stamp(cfg.hit_stamp, f_stamp)
            fr.alpha_composite(st, (W - st.width - 40, 1480))
            if cfg.hit_sub:
                text_block(ImageDraw.Draw(fr), (W // 2, y + 20), wrap(d, cfg.hit_sub, f_sub, W - 160),
                           f_sub, "white", stroke=6)
        else:
            fr.alpha_composite(ghost, lined_up)
            fr.alpha_composite(target, tpos)
            fr.alpha_composite(bag, (tpos[0] - 70, tpos[1] + 150))
            for j, sc in enumerate(scribs[:2]):
                fr.alpha_composite(sc, (min(tpos[0] + 40, W - sc.width - 10), tpos[1] + 430 + j * 280))
            x = round(start_x + k * step)
            fr.alpha_composite(mover, (x, lined_up[1]))
            d = ImageDraw.Draw(fr)
            # red circle on the opponent's face, red X on the fist
            d.ellipse((chin[0] - 80, chin[1] - 120, chin[0] + 90, chin[1] + 20), outline=(235, 40, 40), width=6)
            fxp, fyp = x + fx - 40, lined_up[1] + fy
            if -80 < fxp < W:
                d.line((fxp - 40, fyp - 40, fxp + 40, fyp + 40), fill=(235, 40, 40), width=9)
                d.line((fxp - 40, fyp + 40, fxp + 40, fyp - 40), fill=(235, 40, 40), width=9)
            # hint arrow under the outline
            hx, hy = lined_up[0] + 280, lined_up[1] + mover.height
            d.line((hx - 50, hy + 230, hx, hy + 10), fill="white", width=7)
            d.polygon([(hx - 18, hy + 40), (hx + 16, hy + 46), (hx + 4, hy + 6)], fill="white")
            hint = scribble(cfg.target_hint, f_hint, color=(255, 255, 255), angle=6)
            fr.alpha_composite(hint, (30, hy + 220))
            phase = i // cfg.change_every
            line = taunts[phase % len(taunts)]
            text_block(d, (W // 2, 560), wrap(d, line, f_taunt, W - 220), f_taunt,
                       (255, 230, 40), stroke=6)
            speech_bubble(d, (440, 765, 1058, 895), talk[phase % len(talk)], f_bubble,
                          tail_to=(chin[0] + 5, tpos[1] - 10))

        d = ImageDraw.Draw(fr)
        fh = fit(d, cfg.headline, f_head, W - 100, 9)
        text_block(d, (W // 2, cfg.headline_y), cfg.headline[:1], fh, head_cols[0], stroke=9, spacing=2)
        text_block(d, (W // 2, cfg.headline_y + 115), cfg.headline[1:], fh, head_cols[1], stroke=9)
        fr.convert("RGB").save(tmp / f"f{i:04d}.png")

    if frames_only:
        return tmp
    out = encode(tmp, cfg.out, cfg.audio_loop, cfg.duration)
    shutil.rmtree(tmp, ignore_errors=True)
    return out


def encode(frames: Path, out: Path, audio_loop: Path | None, duration: float) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames / "f%04d.png")]
    if audio_loop:
        cycle = float(subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(audio_loop)]).strip())
        tempo = cycle / duration     # e.g. 6.17s cycle on a 6.0s reel -> atempo 1.029
        cmd += ["-i", str(audio_loop), "-filter:a", f"atempo={tempo:.5f}", "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-t", f"{duration}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
            "-preset", "medium", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)
    return out


def still(cfg: SweepReel, frame: int, out: Path) -> Path:
    """Render one frame (e.g. a hit frame and a miss frame for review)."""
    tmp = Path(tempfile.mkdtemp(prefix="pausegame_still_"))
    saved = cfg.duration
    cfg.duration = (frame + 1) / FPS
    render(cfg, frames_only=tmp)
    cfg.duration = saved
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(tmp / f"f{frame:04d}.png", out)
    shutil.rmtree(tmp, ignore_errors=True)
    return out
