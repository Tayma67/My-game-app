#!/usr/bin/env python3
"""Reusable product asset builder.

Generates, from a Markdown source:
  - a 1280x720 cover PNG (and JPG) with a clean branded design
  - a styled PDF of the content

Usage:
  python3 tools/build_product.py \
      --md products/<slug>/the-kit.md \
      --out-dir products/<slug> \
      --pdf-name "My-Product.pdf" \
      --title "AI Automation" --title2 "Starter Kit" \
      --kicker "NO CODE · NO EXPENSIVE TOOLS" \
      --subtitle "10 copy-paste automations" \
      --badge "For Freelancers & SMBs" \
      --stat "10" --stat-label "blueprints"

Pure-Python deps: Pillow, reportlab. No system tools, no network needed.
"""
import argparse, os, re, html
from PIL import Image, ImageDraw, ImageFont

FB = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"


def _font(path, size):
    return ImageFont.truetype(path, size)


def make_cover(path_png, path_jpg, title, title2, kicker, subtitle, badge,
               stat, stat_label, c0=(15, 23, 42), c1=(30, 58, 138),
               accent=(56, 189, 248), cyan=(34, 211, 238)):
    W, H = 1280, 720
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        for x in range(W):
            t = (x / W + y / H) / 2
            px[x, y] = (int(c0[0] + (c1[0] - c0[0]) * t),
                        int(c0[1] + (c1[1] - c0[1]) * t),
                        int(c0[2] + (c1[2] - c0[2]) * t))
    d = ImageDraw.Draw(img)
    white, grey = (255, 255, 255), (203, 213, 225)
    for ly in (180, 540):
        d.line([(0, ly), (W, ly)], fill=white, width=1)
    for lx in (320, 960):
        d.line([(lx, 0), (lx, H)], fill=white, width=1)
    d.text((80, 215), kicker, font=_font(FB, 30), fill=cyan)
    d.text((78, 270), title, font=_font(FB, 92), fill=white)
    if title2:
        d.text((78, 372), title2, font=_font(FB, 92), fill=accent)
    # subtitle wraps at ~46 chars
    sy = 500
    line = ""
    for word in subtitle.split():
        test = (line + " " + word).strip()
        if d.textlength(test, font=_font(FR, 34)) > 800:
            d.text((80, sy), line, font=_font(FR, 34), fill=grey); sy += 40; line = word
        else:
            line = test
    if line:
        d.text((80, sy), line, font=_font(FR, 34), fill=grey)
    # badge auto-sized
    bf = _font(FB, 24)
    tb = d.textbbox((0, 0), badge, font=bf)
    padx, pady = 28, 16
    bx, by = 80, 612
    bw, bh = (tb[2] - tb[0]) + 2 * padx, (tb[3] - tb[1]) + 2 * pady
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=bh // 2, fill=accent)
    d.text((bx + padx - tb[0], by + pady - tb[1]), badge, font=bf, fill=(15, 23, 42))
    # stat circle
    if stat:
        cx, cy, rad = 1080, 320, 85
        d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=cyan, width=6)
        nf = _font(FB, 70 if len(stat) <= 2 else 50)
        nb = d.textbbox((0, 0), stat, font=nf)
        d.text((cx - (nb[2] - nb[0]) / 2 - nb[0], cy - (nb[3] - nb[1]) / 2 - nb[1]),
               stat, font=nf, fill=white)
        lb = _font(FR, 30)
        lbb = d.textbbox((0, 0), stat_label, font=lb)
        d.text((cx - (lbb[2] - lbb[0]) / 2 - lbb[0], cy + rad + 20), stat_label, font=lb, fill=grey)
    img.save(path_png, "PNG")
    img.save(path_jpg, "JPEG", quality=90)


def make_pdf(md_path, pdf_path, title_meta):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    HRFlowable, Table, TableStyle)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

    DARK = colors.HexColor("#0f172a"); BLUE = colors.HexColor("#1e3a8a")
    ACC = colors.HexColor("#0369a1"); BOXBG = colors.HexColor("#eef2ff")
    GREY = colors.HexColor("#475569")
    ss = getSampleStyleSheet()
    st = {
        "title": ParagraphStyle("t", parent=ss["Title"], fontName="Helvetica-Bold",
                                 fontSize=26, textColor=DARK, spaceAfter=4, leading=30),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontName="Helvetica-Bold",
                              fontSize=15, textColor=BLUE, spaceBefore=14, spaceAfter=6, leading=18),
        "body": ParagraphStyle("b", parent=ss["BodyText"], fontName="Helvetica",
                               fontSize=10.5, textColor=colors.HexColor("#1f2937"), leading=15, spaceAfter=4),
        "bullet": ParagraphStyle("bu", parent=ss["BodyText"], fontName="Helvetica",
                                 fontSize=10.5, leftIndent=12, bulletIndent=2, leading=15, spaceAfter=2),
        "prompt": ParagraphStyle("p", parent=ss["BodyText"], fontName="Helvetica-Oblique",
                                 fontSize=10, textColor=DARK, leading=14),
        "note": ParagraphStyle("n", parent=ss["BodyText"], fontName="Helvetica-Oblique",
                               fontSize=9.5, textColor=GREY, leading=13, spaceAfter=4),
    }

    def inline(t):
        t = html.escape(t)
        t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
        t = re.sub(r"`(.+?)`", r'<font face="Courier">\1</font>', t)
        return t

    story = []

    def flush_quote(buf):
        if not buf:
            return
        p = Paragraph("<br/>".join(inline(x) for x in buf), st["prompt"])
        tbl = Table([[p]], colWidths=[165 * mm])
        tbl.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BOXBG),
                                 ("BOX", (0, 0), (-1, -1), 0.75, ACC),
                                 ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                                 ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        story.append(tbl); story.append(Spacer(1, 5))

    qbuf = []
    for raw in open(md_path, encoding="utf-8").read().split("\n"):
        line = raw.rstrip()
        if line.startswith("> "):
            qbuf.append(line[2:]); continue
        flush_quote(qbuf); qbuf = []
        if not line.strip():
            continue
        if line.startswith("# "):
            story.append(Paragraph(inline(line[2:]), st["title"]))
        elif line.startswith("## "):
            story.append(Paragraph(inline(line[3:]), st["h2"]))
        elif line.startswith("---"):
            story.append(Spacer(1, 3)); story.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#cbd5e1"))); story.append(Spacer(1, 3))
        elif line.startswith("- "):
            story.append(Paragraph(inline(line[2:]), st["bullet"], bulletText="•"))
        elif line.startswith("*[") and line.endswith("]*"):
            story.append(Paragraph(inline(line), st["note"]))
        else:
            story.append(Paragraph(inline(line), st["body"]))
    flush_quote(qbuf)
    SimpleDocTemplate(pdf_path, pagesize=A4, topMargin=18 * mm, bottomMargin=16 * mm,
                      leftMargin=20 * mm, rightMargin=20 * mm, title=title_meta).build(story)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--pdf-name", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--title2", default="")
    ap.add_argument("--kicker", default="")
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--badge", default="")
    ap.add_argument("--stat", default="")
    ap.add_argument("--stat-label", default="")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    make_cover(os.path.join(a.out_dir, "cover.png"), os.path.join(a.out_dir, "cover.jpg"),
               a.title, a.title2, a.kicker, a.subtitle, a.badge, a.stat, a.stat_label)
    make_pdf(a.md, os.path.join(a.out_dir, a.pdf_name), a.title + " " + a.title2)
    print("built:", a.out_dir)


if __name__ == "__main__":
    main()
