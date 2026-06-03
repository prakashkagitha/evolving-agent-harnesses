"""Render BEFORE/AFTER BattleSnake games into GIFs (for the X/Twitter post).

Reads two game JSONL frame files (same seed, same opponent: the parent harness loses,
the evolved harness wins), draws each turn, and writes:
  - before.gif, after.gif        (single-panel)
  - before_after.gif             (side-by-side, the hero artifact)
Pure Pillow, warm Anthropic-style palette to match winning_mutation.svg.
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from cc_gepa.sim import _read_frames

CELL = 38
PAD_TOP = 70           # label strip per panel
PAD = 16
BOARD = 11 * CELL      # 418
PANEL_W = BOARD + 2 * PAD
PANEL_H = BOARD + PAD_TOP + PAD
GAP = 26
HEAD_STRIP = 64        # top headline across the whole side-by-side

BG = (244, 236, 223)        # warm paper
PANEL = (251, 248, 243)
GRID = (230, 220, 204)
INK = (42, 33, 24)
MUTED = (138, 128, 114)
OURS = (194, 96, 58)        # clay = our evolved bot
OURS_LT = (226, 170, 140)
OPP = (107, 114, 128)       # slate = opponent
OPP_LT = (176, 182, 192)
FOOD = (214, 75, 75)
GREEN = (60, 139, 104)
REDX = (181, 84, 62)


def _font(sz, bold=False):
    for p in ([
        "/usr/share/fonts/truetype/inter/Inter-Bold.ttf" if bold else "/usr/share/fonts/truetype/inter/Inter-Regular.ttf",
    ]):
        try:
            return ImageFont.truetype(p, sz)
        except Exception:
            pass
    # fall back to any Inter / DejaVu the system has
    import glob
    pats = ["*Inter*Bold*" if bold else "*Inter*Regular*", "*DejaVuSans-Bold*" if bold else "*DejaVuSans.ttf"]
    for pat in pats:
        for f in glob.glob(f"/usr/share/fonts/**/{pat}.ttf", recursive=True) + \
                 glob.glob(f"/usr/local/share/fonts/**/{pat}", recursive=True):
            try:
                return ImageFont.truetype(f, sz)
            except Exception:
                pass
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", sz)
    except Exception:
        return ImageFont.load_default()


def _ctext(d, xy, s, font, fill, anchor="mm"):
    d.text(xy, s, font=font, fill=fill, anchor=anchor)


def _round(d, box, r, fill):
    d.rounded_rectangle(box, radius=r, fill=fill)


def draw_panel(frame, our_name, label_top, label_sub, result=None):
    """Draw one board state -> a PANEL_W x PANEL_H image."""
    img = Image.new("RGB", (PANEL_W, PANEL_H), PANEL)
    d = ImageDraw.Draw(img)
    # labels
    _ctext(d, (PANEL_W // 2, 24), label_top, _font(22, True), INK)
    _ctext(d, (PANEL_W // 2, 50), label_sub, _font(15), MUTED)
    ox, oy = PAD, PAD_TOP
    # board bg + grid
    _round(d, (ox, oy, ox + BOARD, oy + BOARD), 10, (255, 253, 250))
    for i in range(12):
        d.line((ox + i * CELL, oy, ox + i * CELL, oy + BOARD), fill=GRID, width=1)
        d.line((ox, oy + i * CELL, ox + BOARD, oy + i * CELL), fill=GRID, width=1)
    b = frame["board"]
    W, H = b["width"], b["height"]

    def cell_box(x, y, inset=3):
        px = ox + x * CELL
        py = oy + (H - 1 - y) * CELL          # board y is bottom-up
        return (px + inset, py + inset, px + CELL - inset, py + CELL - inset)

    # food
    for f in b.get("food", []):
        bx = cell_box(f["x"], f["y"], inset=10)
        d.ellipse(bx, fill=FOOD)
    # snakes
    for s in b["snakes"]:
        ours = (s["name"] == our_name)
        base, lt = (OURS, OURS_LT) if ours else (OPP, OPP_LT)
        body = s["body"]
        n = len(body)
        for i, c in enumerate(body):
            # gradient head(base)->tail(lt)
            t = (i / max(n - 1, 1))
            col = tuple(int(base[k] + (lt[k] - base[k]) * t) for k in range(3))
            _round(d, cell_box(c["x"], c["y"], inset=3), 7, col)
        # head accent
        hx, hy = body[0]["x"], body[0]["y"]
        hb = cell_box(hx, hy, inset=3)
        _round(d, hb, 7, base)
        # eyes
        cx, cy = (hb[0] + hb[2]) / 2, (hb[1] + hb[3]) / 2
        for dx in (-5, 5):
            d.ellipse((cx + dx - 2.5, cy - 4.5, cx + dx + 2.5, cy + 0.5), fill=(255, 255, 255))
            d.ellipse((cx + dx - 1.3, cy - 3.3, cx + dx + 1.3, cy - 0.7), fill=(30, 25, 20))
    # turn counter
    _ctext(d, (ox + 4, oy + BOARD + 2), f"turn {frame['turn']}", _font(13), MUTED, anchor="lm")
    # result overlay
    if result:
        txt, col = result
        bw, bh = 188, 52
        bx0 = ox + (BOARD - bw) // 2
        by0 = oy + (BOARD - bh) // 2
        ov = Image.new("RGBA", (bw, bh), (255, 255, 255, 0))
        od = ImageDraw.Draw(ov)
        od.rounded_rectangle((0, 0, bw, bh), radius=14, fill=(255, 255, 255, 235))
        od.rounded_rectangle((0, 0, bw, bh), radius=14, outline=col + (255,), width=3)
        img.paste(ov, (bx0, by0), ov)
        _ctext(d, (ox + BOARD // 2, oy + BOARD // 2), txt, _font(26, True), col)
    return img


def load(path):
    frames, result = _read_frames(path)
    return frames


def build(before_path, after_path, our_before, our_after, opp, outdir, step=2, hold=26):
    fb = load(before_path)[::step]
    fa = load(after_path)[::step]
    lb, la = len(fb), len(fa)
    N = max(lb, la)
    outdir = Path(outdir)

    # ---- side-by-side hero ----
    W = PAD + PANEL_W + GAP + PANEL_W + PAD
    Htot = HEAD_STRIP + PANEL_H + PAD
    frames = []
    for t in range(N + hold):
        canvas = Image.new("RGB", (W, Htot), BG)
        d = ImageDraw.Draw(canvas)
        _ctext(d, (W // 2, 24), "Same opponent, same start — only the harness differs", _font(23, True), INK)
        _ctext(d, (W // 2, 48), "the evolving bot is clay · opponent is grey", _font(14), MUTED)
        bi = min(t, lb - 1)
        ai = min(t, la - 1)
        b_res = ("DEFEAT", REDX) if t >= lb - 1 else None
        a_res = ("VICTORY", GREEN) if t >= la - 1 else None
        pb = draw_panel(fb[bi], our_before, "BEFORE", "space control + food", b_res)
        pa = draw_panel(fa[ai], our_after, "AFTER", "+ combat specialist", a_res)
        canvas.paste(pb, (PAD, HEAD_STRIP))
        canvas.paste(pa, (PAD + PANEL_W + GAP, HEAD_STRIP))
        frames.append(canvas.convert("P", palette=Image.ADAPTIVE, colors=64))
    durs = [70] * N + [60] * hold
    frames[0].save(outdir / "before_after.gif", save_all=True, append_images=frames[1:],
                   duration=durs, loop=0, optimize=True, disposal=2)

    # ---- individual gifs ----
    for tag, fr, our, lab, sub, win in [
        ("before", fb, our_before, "BEFORE", "space control + food", False),
        ("after", fa, our_after, "AFTER", "+ combat specialist", True)]:
        ims = []
        L = len(fr)
        for t in range(L + hold):
            i = min(t, L - 1)
            res = (("VICTORY", GREEN) if win else ("DEFEAT", REDX)) if t >= L - 1 else None
            ims.append(draw_panel(fr[i], our, lab, sub, res).convert("P", palette=Image.ADAPTIVE, colors=64))
        ims[0].save(outdir / f"{tag}.gif", save_all=True, append_images=ims[1:],
                    duration=[70] * L + [60] * hold, loop=0, optimize=True, disposal=2)
    return {"side_by_side": str(outdir / "before_after.gif"), "before": str(outdir / "before.gif"),
            "after": str(outdir / "after.gif"), "frames": N}


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--before"); ap.add_argument("--after")
    ap.add_argument("--our-before", default="before_strong"); ap.add_argument("--our-after", default="after_strong")
    ap.add_argument("--opp", default="strong"); ap.add_argument("--out", default=".")
    ap.add_argument("--step", type=int, default=2)
    ap.add_argument("--sample", action="store_true", help="just write one mid-game composite PNG for review")
    a = ap.parse_args()
    if a.sample:
        fb = load(a.before); fa = load(a.after)
        canvasW = PAD + PANEL_W + GAP + PANEL_W + PAD
        canvasH = HEAD_STRIP + PANEL_H + PAD
        canvas = Image.new("RGB", (canvasW, canvasH), BG)
        d = ImageDraw.Draw(canvas)
        _ctext(d, (canvasW // 2, 24), "Same opponent, same start — only the harness differs", _font(23, True), INK)
        _ctext(d, (canvasW // 2, 48), "the evolving bot is clay · opponent is grey", _font(14), MUTED)
        canvas.paste(draw_panel(fb[len(fb) // 2], a.our_before, "BEFORE", "space control + food"), (PAD, HEAD_STRIP))
        canvas.paste(draw_panel(fa[len(fa) // 2], a.our_after, "AFTER", "+ combat specialist"), (PAD + PANEL_W + GAP, HEAD_STRIP))
        canvas.save(Path(a.out) / "_gif_sample.png")
        print("wrote", Path(a.out) / "_gif_sample.png")
    else:
        print(build(a.before, a.after, a.our_before, a.our_after, a.opp, a.out, step=a.step))
