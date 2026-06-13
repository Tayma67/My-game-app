#!/usr/bin/env python3
"""Generate Etsy-optimized images (2000x1500, 4:3, hi-res) for a product.

Etsy ranks listings largely on first-photo click-through rate, and needs images
>=2000px on the short side (for zoom) in a 4:3 ratio. Our 1280x720 covers are
too small and wrong ratio for Etsy. This produces:
  - etsy-cover.png   : slot 1 thumbnail (4:3, 2000x1500, branded)
  - etsy-preview.png : slot 2 "what's inside" contents list

Usage:
  python3 tools/make_etsy_images.py --md products/<slug>/the-kit.md \
      --out-dir products/<slug> --title "Job Seeker's" --title2 "AI Kit" \
      --subtitle "12 AI prompts ..." --badge "For Job Seekers" \
      --stat "12" --stat-label "prompts"
"""
import argparse, os, re
from PIL import Image, ImageDraw, ImageFont

FB = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
W, H = 2000, 1500
C0, C1 = (15, 23, 42), (30, 58, 138)
ACC, CYAN, WHITE, GREY = (56, 189, 248), (34, 211, 238), (255, 255, 255), (203, 213, 225)


def f(path, s):
    return ImageFont.truetype(path, s)


def gradient_bg():
    # build small, resize up = smooth + fast (no numpy)
    sw, sh = 200, 150
    small = Image.new("RGB", (sw, sh))
    px = small.load()
    for y in range(sh):
        for x in range(sw):
            t = (x / sw + y / sh) / 2
            px[x, y] = (int(C0[0] + (C1[0]-C0[0])*t), int(C0[1] + (C1[1]-C0[1])*t),
                        int(C0[2] + (C1[2]-C0[2])*t))
    return small.resize((W, H), Image.BILINEAR)


def centered(d, cx, y, text, font, fill):
    b = d.textbbox((0, 0), text, font=font)
    d.text((cx - (b[2]-b[0]) / 2 - b[0], y), text, font=font, fill=fill)


def make_cover(out, title, title2, kicker, subtitle, badge, stat, stat_label):
    img = gradient_bg()
    d = ImageDraw.Draw(img)
    for ly in (300, 1200):
        d.line([(0, ly), (W, ly)], fill=WHITE, width=2)
    cx = W // 2
    centered(d, cx, 360, kicker, f(FB, 46), CYAN)
    centered(d, cx, 470, title, f(FB, 150), WHITE)
    if title2:
        centered(d, cx, 640, title2, f(FB, 150), ACC)
    # subtitle wrap
    y = 860
    line = ""
    sf = f(FR, 52)
    for word in subtitle.split():
        test = (line + " " + word).strip()
        if d.textlength(test, font=sf) > 1500:
            centered(d, cx, y, line, sf, GREY); y += 64; line = word
        else:
            line = test
    if line:
        centered(d, cx, y, line, sf, GREY)
    # badge
    bf = f(FB, 44)
    tb = d.textbbox((0, 0), badge, font=bf)
    bw, bh = (tb[2]-tb[0]) + 90, (tb[3]-tb[1]) + 50
    bx, by = cx - bw // 2, 1040
    d.rounded_rectangle([bx, by, bx+bw, by+bh], radius=bh//2, fill=ACC)
    d.text((bx + 45 - tb[0], by + 25 - tb[1]), badge, font=bf, fill=(15, 23, 42))
    # stat chip
    if stat:
        sc = f(FB, 60)
        chip = f"{stat} {stat_label}"
        cb = d.textbbox((0, 0), chip, font=sc)
        cw = (cb[2]-cb[0]) + 70
        d.rounded_rectangle([cx-cw//2, 1180, cx+cw//2, 1180+96], radius=20, outline=CYAN, width=4)
        centered(d, cx, 1198, chip, sc, CYAN)
    img.save(out, "PNG")


def make_preview(out, md_path, title, title2):
    img = gradient_bg()
    d = ImageDraw.Draw(img)
    cx = W // 2
    centered(d, cx, 90, "WHAT'S INSIDE", f(FB, 56), CYAN)
    centered(d, cx, 175, f"{title} {title2}".strip(), f(FB, 70), WHITE)
    # collect numbered prompt headings: "## N. Title"
    items = []
    for raw in open(md_path, encoding="utf-8").read().split("\n"):
        m = re.match(r"^##\s+(\d+\.\s+.+)$", raw.strip())
        if m:
            items.append(m.group(1))
    items = items[:13]
    y = 330
    itf = f(FR, 48)
    for it in items:
        if len(it) > 52:
            it = it[:50] + "…"
        d.ellipse([180, y+14, 210, y+44], fill=ACC)
        d.text((250, y), it, font=itf, fill=WHITE)
        y += 78
    centered(d, cx, 1380, "Instant PDF · Works on a free ChatGPT or Claude account", f(FR, 40), GREY)
    img.save(out, "PNG")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--title2", default="")
    ap.add_argument("--kicker", default="")
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--badge", default="")
    ap.add_argument("--stat", default="")
    ap.add_argument("--stat-label", default="")
    a = ap.parse_args()
    make_cover(os.path.join(a.out_dir, "etsy-cover.png"), a.title, a.title2,
               a.kicker, a.subtitle, a.badge, a.stat, a.stat_label)
    make_preview(os.path.join(a.out_dir, "etsy-preview.png"), a.md, a.title, a.title2)
    print("etsy images:", a.out_dir)


if __name__ == "__main__":
    main()
