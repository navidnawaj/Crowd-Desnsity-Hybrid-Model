"""
build_presentation.py
=====================
Hybrid Crowd Density Estimation — Thesis Presentation (21 slides)
Clean dark-blue theme · Fixed layout · No overflow
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

# ─── Slide dimensions ──────────────────────────────────────────────────────
SLIDE_W = Inches(13.33)
SLIDE_H = Inches(7.5)

# ─── Figure directory ──────────────────────────────────────────────────────
FIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "thesis_figures")

# ─── Colour palette ────────────────────────────────────────────────────────
BG    = RGBColor(0x1E, 0x2A, 0x3A)   # slide background
CARD  = RGBColor(0x24, 0x34, 0x47)   # card fill
CARD2 = RGBColor(0x2D, 0x3F, 0x55)   # accent card fill
BLUE  = RGBColor(0x4F, 0x9C, 0xF9)   # primary accent
LBLUE = RGBColor(0x63, 0xB3, 0xED)   # secondary accent
GREEN = RGBColor(0x48, 0xBB, 0x78)   # success
AMBER = RGBColor(0xF6, 0xAD, 0x55)   # warning
RED   = RGBColor(0xFC, 0x81, 0x81)   # danger
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BODY  = RGBColor(0xE2, 0xE8, 0xF0)   # body text
MUTED = RGBColor(0x94, 0xA3, 0xB8)   # subtext
NAVY  = RGBColor(0x1E, 0x2A, 0x3A)   # table header text bg (same as BG)

# extra tinted fills for stratum cards
DARK_GREEN = RGBColor(0x2A, 0x4A, 0x3A)
DARK_AMBER = RGBColor(0x4A, 0x3A, 0x2A)
DARK_RED   = RGBColor(0x3A, 0x2A, 0x2A)
DARK_BLUEP = RGBColor(0x3B, 0x4F, 0x7A)  # blue-purple for router box


# ───────────────────────────────────────────────────────────────────────────
# LOW-LEVEL HELPERS
# ───────────────────────────────────────────────────────────────────────────

def new_prs():
    prs = Presentation()
    prs.slide_width  = SLIDE_W
    prs.slide_height = SLIDE_H
    return prs


def blank_slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def bg(slide):
    f = slide.background.fill
    f.solid()
    f.fore_color.rgb = BG


def rect(slide, x, y, w, h, fill=CARD, line=False):
    s = slide.shapes.add_shape(1, x, y, w, h)
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if not line:
        s.line.fill.background()
    else:
        s.line.color.rgb = fill
    return s


def txt(slide, text, x, y, w, h, size=12, bold=False, color=BODY,
        align=PP_ALIGN.LEFT, italic=False, wrap=True):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.italic = italic
    r.font.color.rgb = color
    return tb


def img(slide, fname, x, y, w, h=None):
    path = os.path.join(FIG_DIR, fname)
    if not os.path.exists(path):
        # placeholder box so layout still works
        r = rect(slide, x, y, w, h if h else Inches(3), fill=CARD2)
        txt(slide, f"[Missing: {fname}]",
            x + Inches(0.1), y + Inches(0.1),
            w - Inches(0.2), Inches(0.4),
            size=10, color=RED, align=PP_ALIGN.CENTER)
        return
    if h:
        slide.shapes.add_picture(path, x, y, w, h)
    else:
        slide.shapes.add_picture(path, x, y, width=w)


def header_bar(slide):
    rect(slide, 0, 0, SLIDE_W, Inches(0.05), fill=BLUE)


def slide_title(slide, title, subtitle=None):
    header_bar(slide)
    txt(slide, title,
        Inches(0.35), Inches(0.1), Inches(11.5), Inches(0.55),
        size=30, bold=True, color=WHITE)
    if subtitle:
        txt(slide, subtitle,
            Inches(0.35), Inches(0.65), Inches(11.5), Inches(0.38),
            size=14, color=MUTED)


# ───────────────────────────────────────────────────────────────────────────
# CARD HELPER  (with overflow guard)
# ───────────────────────────────────────────────────────────────────────────

def card(slide, x, y, w, h, title=None, bullets=None, fill_color=CARD,
         bullet_color=BODY, title_color=BLUE):
    if bullets is None:
        bullets = []
    rect(slide, x, y, w, h, fill=fill_color)

    pad = Inches(0.12)
    line_h = Inches(0.33)
    title_h = Inches(0.36)

    if title:
        txt(slide, title,
            x + pad, y + Inches(0.1), w - pad * 2, title_h,
            size=13, bold=True, color=title_color)
        bullet_y = y + Inches(0.52)
        available_h = h - Inches(0.52) - Inches(0.08)
    else:
        bullet_y = y + pad
        available_h = h - pad * 2

    max_bullets = max(0, int(available_h / line_h))
    visible = bullets[:max_bullets]

    for b in visible:
        txt(slide, f"• {b}",
            x + pad, bullet_y, w - pad * 2, line_h,
            size=12, color=bullet_color)
        bullet_y += line_h


# ───────────────────────────────────────────────────────────────────────────
# TABLE HELPER
# ───────────────────────────────────────────────────────────────────────────

def table(slide, headers, rows, x, y, col_widths, row_h=Inches(0.45),
          hdr_fill=BLUE, row_fill=CARD, highlight_rows=None):
    """
    Draw a table from rects + text.
    highlight_rows: list of row indices (0-based) to use DARK_GREEN fill.
    """
    if highlight_rows is None:
        highlight_rows = []

    # header
    cx = x
    for i, h in enumerate(headers):
        rect(slide, cx, y, col_widths[i], row_h, fill=hdr_fill)
        txt(slide, h,
            cx + Inches(0.06), y + Inches(0.06),
            col_widths[i] - Inches(0.12), row_h - Inches(0.1),
            size=11, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
        cx += col_widths[i]

    # rows
    for ri, row in enumerate(rows):
        ry = y + row_h * (ri + 1)
        fill = DARK_GREEN if ri in highlight_rows else (CARD2 if ri % 2 == 1 else row_fill)
        cx = x
        for ci, cell in enumerate(row):
            rect(slide, cx, ry, col_widths[ci], row_h, fill=fill)
            c_text = str(cell)
            c_color = BLUE if '★' in c_text else (GREEN if '✓' in c_text else BODY)
            txt(slide, c_text,
                cx + Inches(0.06), ry + Inches(0.05),
                col_widths[ci] - Inches(0.12), row_h - Inches(0.1),
                size=11, color=c_color, align=PP_ALIGN.CENTER)
            cx += col_widths[ci]


# ───────────────────────────────────────────────────────────────────────────
# BUILD ALL 21 SLIDES
# ───────────────────────────────────────────────────────────────────────────

def build(output="thesis_presentation.pptx"):
    prs = new_prs()

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 1 — TITLE
    # ══════════════════════════════════════════════════════════════════════
    s = blank_slide(prs)
    bg(s)

    # top & bottom accent bars
    rect(s, 0, 0, SLIDE_W, Inches(0.08), fill=BLUE)
    rect(s, 0, Inches(7.42), SLIDE_W, Inches(0.08), fill=BLUE)

    # main content box
    rect(s, Inches(0.35), Inches(0.9), Inches(12.6), Inches(4.2), fill=CARD)

    # titles
    txt(s, "Hybrid Crowd Density Estimation",
        Inches(0.35), Inches(1.1), Inches(12.6), Inches(0.75),
        size=42, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    txt(s, "for Edge Deployment",
        Inches(0.35), Inches(1.9), Inches(12.6), Inches(0.65),
        size=38, bold=True, color=BLUE, align=PP_ALIGN.CENTER)
    txt(s, "LCDNet + MobileCount + MobileNetV2 Router",
        Inches(0.35), Inches(2.65), Inches(12.6), Inches(0.45),
        size=16, color=MUTED, align=PP_ALIGN.CENTER)

    # divider
    rect(s, Inches(2.5), Inches(3.2), Inches(8.3), Inches(0.04), fill=BLUE)

    # stat boxes
    stat_data = [
        (Inches(0.9),  "4.35M params",  "Total Deployed Parameters"),
        (Inches(4.76), "MAE 180.9",     "Best System (NWPU val)"),
        (Inches(8.62), "~55 ms",        "Avg Latency (RTX 3050)"),
    ]
    for sx, val, lbl in stat_data:
        rect(s, sx, Inches(3.4), Inches(3.8), Inches(1.35), fill=CARD2)
        txt(s, val,
            sx, Inches(3.6), Inches(3.8), Inches(0.55),
            size=26, bold=True, color=BLUE, align=PP_ALIGN.CENTER)
        txt(s, lbl,
            sx, Inches(4.25), Inches(3.8), Inches(0.38),
            size=11, color=MUTED, align=PP_ALIGN.CENTER)

    # footer
    txt(s, "NWPU-Crowd · ShanghaiTech Part A & B · PyTorch 2.6 · RTX 3050",
        Inches(0.35), Inches(5.05), Inches(12.6), Inches(0.38),
        size=11, color=MUTED, align=PP_ALIGN.CENTER)

    # team box
    rect(s, Inches(2.0), Inches(5.5), Inches(9.3), Inches(1.5), fill=CARD)
    txt(s, "Group Thesis Presentation · 5-Member Team",
        Inches(2.0), Inches(5.65), Inches(9.3), Inches(0.42),
        size=14, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    txt(s, "Dept. of Computer Science & Engineering",
        Inches(2.0), Inches(6.1), Inches(9.3), Inches(0.38),
        size=12, color=MUTED, align=PP_ALIGN.CENTER)

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 2 — BACKGROUND & MOTIVATION
    # ══════════════════════════════════════════════════════════════════════
    s = blank_slide(prs)
    bg(s)
    slide_title(s, "Background & Motivation",
                "Why does crowd estimation need a hybrid approach?")

    card(s, Inches(0.35), Inches(1.15), Inches(3.9), Inches(5.8),
         title="The Problem",
         bullets=[
             "Crowd incidents cause fatalities",
             "Manual counting: slow, error-prone",
             "Cloud systems: latency + privacy risk",
             "GDPR: raw video = personal data",
             "Edge hardware: 5–10W power budget",
         ])

    card(s, Inches(4.45), Inches(1.15), Inches(3.9), Inches(5.8),
         title="Single-Model Dilemma",
         bullets=[
             "Heavy models accurate on dense scenes but need 16M+ params",
             "Lightweight models fast but fail on dense crowds",
             "NWPU counts range: 0 – 20,033",
             "No single lightweight model handles both",
         ])

    card(s, Inches(8.55), Inches(1.15), Inches(4.45), Inches(5.8),
         title="Our Solution",
         fill_color=CARD2,
         bullet_color=GREEN,
         bullets=[
             "Router dispatches each image to best model",
             "LCDNet: sparse scenes (≤100 people)",
             "MobileCount: dense scenes (>100)",
             "4.35M params · 55ms · on-device",
         ])

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 3 — RESEARCH OBJECTIVES
    # ══════════════════════════════════════════════════════════════════════
    s = blank_slide(prs)
    bg(s)
    slide_title(s, "Research Objectives")

    objectives = [
        "Build a fully lightweight hybrid pipeline (≤5M params) for edge crowd density estimation",
        "Train and domain-adapt specialists: LCDNet for sparse, distilled MobileCount for dense",
        "Design a MobileNetV2 router that automatically routes images without human intervention",
        "Apply knowledge distillation (CSRNet teacher → MobileCount student) for free accuracy gain",
        "Evaluate on NWPU-Crowd validation (500 images) — zero-shot on ShanghaiTech A & B",
        "Quantify accuracy-efficiency trade-off: oracle, ablation, calibration, threshold analyses",
    ]

    row_h   = Inches(0.82)
    row_gap = Inches(0.06)
    y_start = Inches(1.15)

    for i, obj in enumerate(objectives):
        oy = y_start + (row_h + row_gap) * i
        # badge
        rect(s, Inches(0.35), oy, Inches(0.55), row_h, fill=BLUE)
        txt(s, str(i + 1),
            Inches(0.35), oy + Inches(0.22), Inches(0.55), Inches(0.38),
            size=18, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
        # content
        rect(s, Inches(0.95), oy, Inches(12.05), row_h, fill=CARD)
        txt(s, obj,
            Inches(1.08), oy + Inches(0.2), Inches(11.8), Inches(0.55),
            size=13, color=BODY)

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 4 — DATASETS
    # ══════════════════════════════════════════════════════════════════════
    s = blank_slide(prs)
    bg(s)
    slide_title(s, "Datasets",
                "NWPU-Crowd: primary · ShanghaiTech A & B: zero-shot evaluation only")

    ds_data = [
        (Inches(0.35),  Inches(4.05), GREEN, "PRIMARY DATASET",
         "NWPU-Crowd",
         ["5,109 total images", "2,133,375 annotations",
          "Count: 0 – 20,033 per image",
          "Train 3,109 · Val 500 · Test 1,500",
          "Threshold T=100 for routing labels"]),
        (Inches(4.6),   Inches(4.05), AMBER, "CROSS-DATASET (EVAL ONLY)",
         "ShanghaiTech Part A",
         ["182 test images", "241,677 head annotations",
          "Count range: 33 – 3,139",
          "Predominantly dense urban scenes",
          "Never used in training"]),
        (Inches(8.85),  Inches(4.15), AMBER, "CROSS-DATASET (EVAL ONLY)",
         "ShanghaiTech Part B",
         ["316 test images", "88,488 head annotations",
          "Count range: 9 – 578",
          "Predominantly sparse street scenes",
          "Never used in training"]),
    ]

    card_h = Inches(5.7)
    for dx, dw, accent, badge, ds_name, stats in ds_data:
        rect(s, dx, Inches(1.15), dw, card_h, fill=CARD)
        # accent bar
        rect(s, dx, Inches(1.15), dw, Inches(0.4), fill=accent)
        txt(s, badge,
            dx + Inches(0.1), Inches(1.15), dw - Inches(0.2), Inches(0.4),
            size=10, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
        # dataset name
        txt(s, ds_name,
            dx + Inches(0.1), Inches(1.65), dw - Inches(0.2), Inches(0.42),
            size=15, bold=True, color=WHITE)
        # stats
        by = Inches(2.15)
        for stat in stats:
            txt(s, f"• {stat}",
                dx + Inches(0.12), by, dw - Inches(0.24), Inches(0.38),
                size=13, color=BODY)
            by += Inches(0.75)

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 5 — SYSTEM ARCHITECTURE
    # ══════════════════════════════════════════════════════════════════════
    s = blank_slide(prs)
    bg(s)
    slide_title(s, "System Architecture",
                "End-to-end hybrid inference pipeline — all inference on-device")

    pipe_boxes = [
        (Inches(0.35),  CARD2,       "INPUT\nIMAGE\n384×384",         WHITE,  14),
        (Inches(2.83),  DARK_BLUEP,  "MobileNetV2\nROUTER\n2.55M params\n4.8ms GPU", WHITE, 13),
        (Inches(5.31),  RGBColor(0x2A, 0x4A, 0x3A),
                                     "LCDNet\nSPARSE\n0.92M\n23ms",   GREEN,  13),
        (Inches(7.79),  DARK_AMBER,  "MobileCount\nDEPLOYED\n0.88M\n3.4ms", AMBER, 13),
        (Inches(10.27), CARD2,       "DENSITY\nMAP\n→ COUNT",         BLUE,   14),
    ]
    box_w = Inches(2.4)
    box_y = Inches(1.8)
    box_h = Inches(3.5)

    for bx, bfill, label, bcolor, bsize in pipe_boxes:
        rect(s, bx, box_y, box_w, box_h, fill=bfill)
        txt(s, label,
            bx + Inches(0.08), box_y + Inches(0.6),
            box_w - Inches(0.16), box_h - Inches(0.8),
            size=bsize, bold=True, color=bcolor, align=PP_ALIGN.CENTER)

    # arrows between boxes
    arrow_xs = [Inches(2.75), Inches(5.23), Inches(7.71), Inches(10.19)]
    for ax in arrow_xs:
        rect(s, ax, Inches(2.9), Inches(0.08), Inches(0.5), fill=BLUE)

    # routing labels under router box
    txt(s, "P(dense) ≥ 0.85 → MC",
        Inches(2.83), Inches(5.45), Inches(2.4), Inches(0.35),
        size=10, color=MUTED, align=PP_ALIGN.CENTER)
    txt(s, "P(dense) < 0.85 → LCD",
        Inches(2.83), Inches(5.8), Inches(2.4), Inches(0.35),
        size=10, color=MUTED, align=PP_ALIGN.CENTER)

    # stat bar
    txt(s, "Total: 4.35M params · 73.3% smaller than CSRNet · Dense path ~8ms · Sparse path ~28ms",
        Inches(0.35), Inches(5.5), Inches(12.6), Inches(0.38),
        size=12, color=MUTED, align=PP_ALIGN.CENTER)

    # note box
    rect(s, Inches(0.35), Inches(6.1), Inches(12.6), Inches(0.85), fill=CARD)
    txt(s, "CSRNet (16.26M params) — KD teacher during training ONLY — never deployed at inference",
        Inches(0.35), Inches(6.25), Inches(12.6), Inches(0.5),
        size=12, color=RED, align=PP_ALIGN.CENTER, italic=True)

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 6 — PREPROCESSING
    # ══════════════════════════════════════════════════════════════════════
    s = blank_slide(prs)
    bg(s)
    slide_title(s, "Preprocessing Pipeline",
                "Adaptive Gaussian density map generation from head point annotations")

    img(s, "figure_4_2_density_pipeline.png",
        Inches(0.35), Inches(1.15), Inches(12.6), Inches(3.6))

    # left panel
    rect(s, Inches(0.35), Inches(4.9), Inches(6.2), Inches(2.15), fill=CARD)
    txt(s, "Density Map Formula",
        Inches(0.47), Inches(5.0), Inches(5.96), Inches(0.36),
        size=13, bold=True, color=BLUE)
    txt(s, "σᵢ = β · d̄ᵢ   (β = 0.3, k = 3 neighbours)",
        Inches(0.47), Inches(5.4), Inches(5.96), Inches(0.38),
        size=14, bold=True, color=WHITE)
    formula_bullets = [
        "d̄ᵢ = mean dist to 3 nearest annotations",
        "Mass conservation: ∬D = N (head count)",
        "Fallback σ = 15px for single annotations",
        "σ clipped to [4.0, 30.0] pixels",
    ]
    fy = Inches(5.82)
    for fb in formula_bullets:
        txt(s, f"• {fb}", Inches(0.47), fy, Inches(5.96), Inches(0.33), size=12, color=BODY)
        fy += Inches(0.33)

    # right panel
    rect(s, Inches(6.75), Inches(4.9), Inches(6.2), Inches(2.15), fill=CARD)
    txt(s, "Data Augmentation",
        Inches(6.87), Inches(5.0), Inches(5.96), Inches(0.36),
        size=13, bold=True, color=BLUE)
    aug_bullets = [
        "Horizontal flip (p=0.5)",
        "Random 384×384 crop from 512×512 (p=0.3)",
        "Brightness/contrast ±20%",
        "Applied to image AND density map equally",
        "ImageNet normalisation: mean [0.485, 0.456, 0.406]",
    ]
    ay = Inches(5.4)
    for ab in aug_bullets:
        txt(s, f"• {ab}", Inches(6.87), ay, Inches(5.96), Inches(0.33), size=12, color=BODY)
        ay += Inches(0.33)

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 7 — LCDNET
    # ══════════════════════════════════════════════════════════════════════
    s = blank_slide(prs)
    bg(s)
    slide_title(s, "LCDNet — Sparse Scene Specialist",
                "Depthwise-separable encoder-decoder · Full-resolution output · 0.917M parameters")

    img(s, "figure_4_4_lcdnet.png",
        Inches(0.35), Inches(1.15), Inches(7.5), Inches(3.8))

    # right panel
    rect(s, Inches(8.05), Inches(1.15), Inches(5.25), Inches(3.8), fill=CARD)
    txt(s, "Architecture Summary",
        Inches(8.17), Inches(1.25), Inches(5.01), Inches(0.36),
        size=13, bold=True, color=BLUE)
    table(s,
          ["Stage", "Output", "Params"],
          [
              ["Encoder 1",  "192×192×64",  "~3.5K"],
              ["Encoder 2-4","...",          "~347K"],
              ["Decoder 1-3","...",          "~520K"],
              ["Output Head","384×384×1",   "~18.5K"],
              ["TOTAL",      "",             "0.917M"],
          ],
          Inches(8.17), Inches(1.65),
          [Inches(1.75), Inches(1.75), Inches(1.6)],
          row_h=Inches(0.42))

    # bottom panel
    rect(s, Inches(0.35), Inches(5.1), Inches(12.6), Inches(1.9), fill=CARD)
    txt(s, "Key Design Choices",
        Inches(0.5), Inches(5.2), Inches(12.3), Inches(0.36),
        size=13, bold=True, color=BLUE)

    col1_bullets = [
        "~8× fewer params via depthwise separable convolutions",
        "Skip connections preserve fine spatial details",
    ]
    col2_bullets = [
        "Full resolution output — better accuracy than 1/8 res",
        "Domain-adapted on NWPU sparse → sparse MAE: 273 → 21.5",
    ]
    by7 = Inches(5.6)
    for b in col1_bullets:
        txt(s, f"• {b}", Inches(0.5), by7, Inches(6.1), Inches(0.33), size=12, color=BODY)
        by7 += Inches(0.33)
    by7 = Inches(5.6)
    for b in col2_bullets:
        txt(s, f"• {b}", Inches(6.75), by7, Inches(6.1), Inches(0.33), size=12, color=BODY)
        by7 += Inches(0.33)

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 8 — MOBILECOUNT + KD
    # ══════════════════════════════════════════════════════════════════════
    s = blank_slide(prs)
    bg(s)
    slide_title(s, "MobileCount + Knowledge Distillation",
                "Dense specialist with CSRNet teacher (training only) · 0.884M deployed")

    img(s, "figure_4_3_distillation.png",
        Inches(0.35), Inches(1.15), Inches(7.5), Inches(4.0))

    # right panel
    rect(s, Inches(8.05), Inches(1.15), Inches(5.25), Inches(4.0), fill=CARD)
    txt(s, "Distillation Results",
        Inches(8.17), Inches(1.25), Inches(5.01), Inches(0.36),
        size=13, bold=True, color=BLUE)
    table(s,
          ["Metric", "Baseline", "Distilled"],
          [
              ["MAE",      "213.2",  "198.7 ✓"],
              ["RMSE",     "803.6",  "778.5"],
              ["Params",   "0.884M", "0.884M (same)"],
              ["GFLOPs",   "1.07",   "1.07 (same)"],
              ["GPU (ms)", "3.4",    "3.4 (same)"],
          ],
          Inches(8.17), Inches(1.65),
          [Inches(1.55), Inches(1.75), Inches(1.9)],
          row_h=Inches(0.48))

    # bottom panel
    rect(s, Inches(0.35), Inches(5.25), Inches(12.6), Inches(1.75), fill=CARD)

    # left half — loss formula
    txt(s, "Loss: L = 0.5·MSE(student,GT) + 0.5·MSE(student,teacher) + 0.05·L1(count)",
        Inches(0.5), Inches(5.35), Inches(7.35), Inches(0.55),
        size=13, bold=True, color=WHITE)
    txt(s, "• 12 epochs · AdamW lr=5×10⁻⁵ · Best at epoch 9 · ~4hrs RTX 3050",
        Inches(0.5), Inches(5.95), Inches(7.35), Inches(0.38),
        size=12, color=MUTED)

    # right half — callout
    txt(s, "−14.5 MAE",
        Inches(8.05), Inches(5.35), Inches(4.75), Inches(0.65),
        size=28, bold=True, color=GREEN, align=PP_ALIGN.CENTER)
    txt(s, "at ZERO deployment cost",
        Inches(8.05), Inches(6.0), Inches(4.75), Inches(0.38),
        size=12, color=MUTED, align=PP_ALIGN.CENTER)

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 9 — KD TRAINING CURVE
    # ══════════════════════════════════════════════════════════════════════
    s = blank_slide(prs)
    bg(s)
    slide_title(s, "Knowledge Distillation Training",
                "Per-epoch validation MAE · NWPU-Crowd full validation set (500 images)")

    img(s, "figure_5_20_kd_delta.png",
        Inches(0.5), Inches(1.15), Inches(12.3), Inches(5.85))

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 10 — ROUTER TRAINING
    # ══════════════════════════════════════════════════════════════════════
    s = blank_slide(prs)
    bg(s)
    slide_title(s, "Routing Classifier Training",
                "MobileNetV2 binary classifier · routing threshold T = 100")

    img(s, "figure_4_8_router_training.png",
        Inches(0.35), Inches(1.15), Inches(8.2), Inches(5.25))

    # right panel
    rect(s, Inches(8.75), Inches(1.15), Inches(4.25), Inches(5.25), fill=CARD)
    txt(s, "Final Metrics",
        Inches(8.87), Inches(1.25), Inches(4.01), Inches(0.36),
        size=13, bold=True, color=BLUE)

    metrics10 = [
        ("Val Accuracy",    "88.80%"),
        ("ECE (calibration)", "0.095"),
        ("Parameters",      "2.552M"),
        ("GFLOPs",          "0.33"),
        ("GPU latency",     "4.8 ms"),
        ("CPU latency",     "8.9 ms"),
        ("Best epoch",      "10 / 25"),
        ("Train time",      "85.6 min"),
    ]
    my10 = Inches(1.65)
    for mk, mv in metrics10:
        txt(s, mk,
            Inches(8.87), my10, Inches(2.2), Inches(0.5),
            size=11, color=MUTED)
        txt(s, mv,
            Inches(11.1), my10, Inches(1.8), Inches(0.5),
            size=11, bold=True, color=BODY, align=PP_ALIGN.RIGHT)
        my10 += Inches(0.56)

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 11 — MAIN RESULTS
    # ══════════════════════════════════════════════════════════════════════
    s = blank_slide(prs)
    bg(s)
    slide_title(s, "Primary Evaluation Results",
                "NWPU-Crowd Validation · 500 images · all checkpoints evaluated on RTX 3050")

    img(s, "figure_5_1_system_comparison.png",
        Inches(0.35), Inches(1.15), Inches(7.5), Inches(4.15))

    table(s,
          ["Config", "MAE", "RMSE", "Params"],
          [
              ["LCDNet Only",           "348.0", "1034",  "0.92M"],
              ["MC (baseline)",         "213.2", "803.6", "0.88M"],
              ["MC (distilled)",        "198.7", "778.5", "0.88M"],
              ["Hybrid-Hard",           "183.0", "787.7", "4.35M"],
              ["Hybrid-Soft",           "182.6", "763.8", "4.35M"],
              ["★ BEST (dist,p*=.85)",  "180.9", "763.6", "4.35M"],
              ["Oracle UB",             "166.6", "751.1", "—"],
          ],
          Inches(8.0), Inches(1.15),
          [Inches(2.15), Inches(0.85), Inches(1.0), Inches(1.3)],
          row_h=Inches(0.52),
          highlight_rows=[5])

    # bottom findings
    rect(s, Inches(0.35), Inches(5.4), Inches(12.6), Inches(1.65), fill=CARD)
    findings11 = [
        "Hybrid beats both standalone specialists: 180.9 vs 198.7 (MC) and 348.0 (LCDNet)",
        "Outperforms NWPU-Crowd paper baseline (MAE 218.0) by 37.1 MAE points",
        "Gap to oracle (166.6) = 14.3 MAE = cost of ~11% router misclassification",
    ]
    fy11 = Inches(5.5)
    for fb in findings11:
        txt(s, f"• {fb}", Inches(0.5), fy11, Inches(12.3), Inches(0.38), size=12, color=BODY)
        fy11 += Inches(0.38)

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 12 — STRATIFIED MAE
    # ══════════════════════════════════════════════════════════════════════
    s = blank_slide(prs)
    bg(s)
    slide_title(s, "Density-Stratified Evaluation",
                "Performance breakdown by crowd density level")

    img(s, "figure_5_2_stratified_mae.png",
        Inches(0.35), Inches(1.15), Inches(7.5), Inches(4.3))

    strata = [
        (Inches(1.15),  DARK_GREEN, "SPARSE ≤100 · n=181",
         "MobileCount: 84.5 → Hybrid: 33.6 → −60.2%!", GREEN),
        (Inches(2.55),  CARD,       "MEDIUM 100–500 · n=229",
         "MC: 98.4 → Hybrid: 99.5 → routing neutral", BODY),
        (Inches(3.95),  DARK_RED,   "DENSE >500 · n=90",
         "MC: 683.6 → Hybrid: 692.8 → both saturate", RED),
    ]
    for sy, sfill, slabel, sval, scolor in strata:
        rect(s, Inches(8.0), sy, Inches(5.3), Inches(1.3), fill=sfill)
        txt(s, slabel,
            Inches(8.12), sy + Inches(0.08), Inches(5.06), Inches(0.36),
            size=12, bold=True, color=WHITE)
        txt(s, sval,
            Inches(8.12), sy + Inches(0.5), Inches(5.06), Inches(0.38),
            size=13, bold=True, color=scolor)

    # bottom
    rect(s, Inches(0.35), Inches(5.55), Inches(12.6), Inches(1.5), fill=CARD)
    txt(s, "Routing's primary benefit is the sparse stratum: 60.2% MAE reduction.",
        Inches(0.5), Inches(5.65), Inches(12.3), Inches(0.38),
        size=13, bold=True, color=WHITE)
    txt(s, "In deployments where sparse scenes dominate (indoor, low-traffic), the advantage grows substantially.",
        Inches(0.5), Inches(6.05), Inches(12.3), Inches(0.38),
        size=12, color=MUTED)
    txt(s, "Extreme density (>3,000): both models saturate — fundamental capacity limit, not a routing issue.",
        Inches(0.5), Inches(6.43), Inches(12.3), Inches(0.38),
        size=12, color=MUTED)

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 13 — THRESHOLD SWEEP
    # ══════════════════════════════════════════════════════════════════════
    s = blank_slide(prs)
    bg(s)
    slide_title(s, "Routing Threshold Optimisation",
                "Post-training calibration · no retraining required · free performance gain")

    img(s, "figure_5_3_threshold.png",
        Inches(0.35), Inches(1.15), Inches(7.9), Inches(4.3))

    rect(s, Inches(8.45), Inches(1.15), Inches(4.55), Inches(4.3), fill=CARD)
    txt(s, "Sweep Results",
        Inches(8.57), Inches(1.25), Inches(4.31), Inches(0.36),
        size=13, bold=True, color=BLUE)
    table(s,
          ["p*", "MAE"],
          [
              ["p* = 0.50 (default)", "182.45"],
              ["p* = 0.70",           "181.58"],
              ["p* = 0.75",           "180.93"],
              ["★ p* = 0.85 (BEST)",  "180.92"],
              ["p* = 0.90",           "185.05"],
          ],
          Inches(8.57), Inches(1.65),
          [Inches(2.9), Inches(1.65)],
          row_h=Inches(0.6),
          highlight_rows=[3])

    rect(s, Inches(0.35), Inches(5.55), Inches(12.6), Inches(1.5), fill=CARD)
    sweep_bullets = [
        "Stable zone p* ∈ [0.70, 0.85]: MAE varies < 1 point — robust to threshold choice",
        "p* = 0.85 routes to MobileCount only when router is ≥85% confident the scene is dense",
        "Best gain: −1.5 MAE vs default argmax (p*=0.50) with zero retraining cost",
    ]
    sy13 = Inches(5.65)
    for sb in sweep_bullets:
        txt(s, f"• {sb}", Inches(0.5), sy13, Inches(12.3), Inches(0.38), size=12, color=BODY)
        sy13 += Inches(0.38)

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 14 — ABLATION
    # ══════════════════════════════════════════════════════════════════════
    s = blank_slide(prs)
    bg(s)
    slide_title(s, "Ablation Study",
                "Isolating the contribution of each design decision")

    img(s, "figure_5_4_ablation.png",
        Inches(0.35), Inches(1.15), Inches(7.5), Inches(3.5))

    # 4 finding cards
    ablation_cards = [
        (DARK_GREEN, "+17.8 MAE if remove routing → Routing is the DOMINANT contributor"),
        (CARD,       "+2.1 MAE if remove KD → Distillation: free accuracy gain"),
        (CARD,       "+1.5 MAE if skip threshold sweep → Calibration: zero-cost gain"),
        (DARK_AMBER, "+1.7 MAE with soft fusion → Soft fusion excluded: no benefit"),
    ]
    ay14 = Inches(1.15)
    for afill, atext in ablation_cards:
        rect(s, Inches(8.0), ay14, Inches(5.3), Inches(0.78), fill=afill)
        txt(s, atext,
            Inches(8.12), ay14 + Inches(0.12), Inches(5.06), Inches(0.55),
            size=12, color=BODY)
        ay14 += Inches(0.82)

    img(s, "figure_5_22_waterfall.png",
        Inches(0.35), Inches(4.75), Inches(12.6), Inches(2.3))

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 15 — CALIBRATION
    # ══════════════════════════════════════════════════════════════════════
    s = blank_slide(prs)
    bg(s)
    slide_title(s, "Router Performance & Calibration",
                "Accuracy · ECE · Confusion Matrix · Confidence Distribution")

    img(s, "figure_5_19_confusion_matrix.png",
        Inches(0.35), Inches(1.15), Inches(5.8), Inches(5.9))
    img(s, "figure_5_6_calibration.png",
        Inches(6.4), Inches(1.15), Inches(6.9), Inches(5.9))

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 16 — ERROR ANALYSIS
    # ══════════════════════════════════════════════════════════════════════
    s = blank_slide(prs)
    bg(s)
    slide_title(s, "Error Distribution & Failure Cases",
                "Understanding the heavy tail and catastrophic misroutes")

    img(s, "figure_5_7_error_hist.png",
        Inches(0.35), Inches(1.15), Inches(7.3), Inches(3.8))
    img(s, "figure_5_9_scatter.png",
        Inches(7.75), Inches(1.15), Inches(5.5), Inches(3.8))

    # failure table
    col_w16 = [Inches(1.0), Inches(1.3), Inches(1.4), Inches(8.9)]
    table(s,
          ["Image", "GT", "Predicted", "Root Cause"],
          [
              ["3234", "12,924", "10 (LCDNet)",  "Router 99% confident sparse — catastrophic miss (~25 MAE impact)"],
              ["3408", "9,728",  "2,428 (MC)",    "Both specialists saturate — model capacity limit"],
              ["3353", "7,122",  "2,077 (MC)",    "Density beyond 0.88M parameter capacity"],
          ],
          Inches(0.35), Inches(5.1),
          col_w16,
          row_h=Inches(0.52))

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 17 — CROSS DATASET
    # ══════════════════════════════════════════════════════════════════════
    s = blank_slide(prs)
    bg(s)
    slide_title(s, "Cross-Dataset Zero-Shot Generalisation",
                "Trained on NWPU-Crowd only · ShanghaiTech never seen during training")

    img(s, "figure_5_8_cross_dataset.png",
        Inches(0.35), Inches(1.15), Inches(12.6), Inches(4.2))

    # result panels
    rect(s, Inches(0.35), Inches(5.45), Inches(6.1), Inches(1.6), fill=DARK_GREEN)
    txt(s, "ShanghaiTech Part B (sparse-dominated, 316 images)",
        Inches(0.47), Inches(5.55), Inches(5.86), Inches(0.38),
        size=12, bold=True, color=WHITE)
    txt(s, "LCDNet: 74.1 · MC: 41.7 · Hybrid: 35.2 ✓ · Oracle: 29.3",
        Inches(0.47), Inches(5.95), Inches(5.86), Inches(0.38),
        size=12, color=GREEN)
    txt(s, "→ Hybrid beats both standalone models",
        Inches(0.47), Inches(6.33), Inches(5.86), Inches(0.38),
        size=11, color=WHITE)

    rect(s, Inches(6.65), Inches(5.45), Inches(6.3), Inches(1.6), fill=CARD)
    txt(s, "ShanghaiTech Part A (dense-dominated, 182 images)",
        Inches(6.77), Inches(5.55), Inches(6.06), Inches(0.38),
        size=12, bold=True, color=WHITE)
    txt(s, "LCDNet: 340.2 · MC: 132.3 · Hybrid: 133.1 ≈ tie · Oracle: 125.7",
        Inches(6.77), Inches(5.95), Inches(6.06), Inches(0.38),
        size=12, color=AMBER)
    txt(s, "→ 95.1% routed to MobileCount — expected tie",
        Inches(6.77), Inches(6.33), Inches(6.06), Inches(0.38),
        size=11, color=WHITE)

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 18 — EFFICIENCY
    # ══════════════════════════════════════════════════════════════════════
    s = blank_slide(prs)
    bg(s)
    slide_title(s, "Edge-Deployment Efficiency Profile",
                "Params · GFLOPs · GPU + CPU latency · vs CSRNet baseline")

    img(s, "figure_5_5_pareto.png",
        Inches(0.35), Inches(1.15), Inches(7.5), Inches(4.15))

    table(s,
          ["Component", "Params", "GFLOPs", "GPU ms", "CPU ms"],
          [
              ["Router",        "2.552M", "0.33", "4.8",   "8.9"],
              ["LCDNet",        "0.917M", "14.59","23.1",  "208.8"],
              ["MobileCount",   "0.884M", "1.07", "3.4",   "13.5"],
              ["TOTAL SYSTEM",  "4.354M", "—",    "~55 avg","~210 avg"],
              ["CSRNet†",       "16.26M", "—",    "N/A",   "N/A"],
          ],
          Inches(8.0), Inches(1.15),
          [Inches(1.6), Inches(0.9), Inches(0.9), Inches(0.95), Inches(1.0)],
          row_h=Inches(0.55),
          highlight_rows=[3])

    rect(s, Inches(0.35), Inches(5.4), Inches(12.6), Inches(1.65), fill=CARD)
    txt(s, "† CSRNet is training-time teacher only — never deployed · vs CSRNet: 73.3% smaller",
        Inches(0.5), Inches(5.5), Inches(12.3), Inches(0.38),
        size=12, color=RED)
    txt(s, "Dense path: Router + MobileCount ≈ 8ms GPU  ·  Sparse path: Router + LCDNet ≈ 28ms GPU",
        Inches(0.5), Inches(5.9), Inches(12.3), Inches(0.38),
        size=12, color=BODY)
    txt(s, "All measurements: NVIDIA RTX 3050 8GB · Jetson Nano deployment = future work",
        Inches(0.5), Inches(6.3), Inches(12.3), Inches(0.38),
        size=11, color=MUTED)

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 19 — PUBLISHED COMPARISON
    # ══════════════════════════════════════════════════════════════════════
    s = blank_slide(prs)
    bg(s)
    slide_title(s, "Comparison with Published Methods")

    # left table
    txt(s, "NWPU-Crowd Validation",
        Inches(0.35), Inches(1.15), Inches(6.2), Inches(0.38),
        size=13, bold=True, color=BLUE)
    table(s,
          ["Method", "Year", "MAE", "Params"],
          [
              ["Dataset baseline", "2020", "218.0", "—"],
              ["CSRNet",           "2018", "~121",  "16.26M"],
              ["MC (baseline)",    "2024", "213.2", "0.88M"],
              ["MC (distilled)",   "2024", "198.7", "0.88M"],
              ["★ Hybrid (ours)",  "2024", "180.9", "4.35M"],
          ],
          Inches(0.35), Inches(1.55),
          [Inches(2.5), Inches(0.7), Inches(0.9), Inches(2.1)],
          row_h=Inches(0.6),
          highlight_rows=[4])

    # right table
    txt(s, "ShanghaiTech Part A (zero-shot)",
        Inches(6.75), Inches(1.15), Inches(6.55), Inches(0.38),
        size=13, bold=True, color=BLUE)
    table(s,
          ["Method", "Year", "MAE", "Params"],
          [
              ["MCNN",           "2016", "110.2", "~1M"],
              ["CSRNet",         "2018", "68.2",  "16.3M"],
              ["SANet",          "2018", "67.0",  "~10M"],
              ["CAN",            "2019", "62.3",  "~5M"],
              ["★ Hybrid*",      "2024", "133.1", "4.35M (zero-shot)"],
          ],
          Inches(6.75), Inches(1.55),
          [Inches(2.2), Inches(0.7), Inches(0.9), Inches(2.75)],
          row_h=Inches(0.6),
          highlight_rows=[4])

    rect(s, Inches(0.35), Inches(5.75), Inches(12.6), Inches(1.3), fill=CARD)
    txt(s, "* Hybrid trained on NWPU-Crowd only — zero-shot evaluation on ShanghaiTech. MAE gap = domain shift penalty.",
        Inches(0.5), Inches(5.85), Inches(12.3), Inches(0.38),
        size=12, color=AMBER, italic=True)
    txt(s, "Key: 4.35M params vs 5–16M for dedicated methods — competitive efficiency at a fraction of the cost.",
        Inches(0.5), Inches(6.25), Inches(12.3), Inches(0.38),
        size=12, color=WHITE)

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 20 — CONCLUSION
    # ══════════════════════════════════════════════════════════════════════
    s = blank_slide(prs)
    bg(s)
    slide_title(s, "Conclusion & Future Work")

    contributions = [
        ("Hybrid System",           "MAE 180.9 · beats both standalone specialists · outperforms NWPU baseline (218.0)"),
        ("Edge-Deployable",         "4.35M params · 73.3% smaller than CSRNet · ~55ms/image on RTX 3050"),
        ("Knowledge Distillation",  "CSRNet→MobileCount: −14.5 MAE at zero deployment cost · 18.4× smaller"),
        ("Cross-Dataset",           "ShanghaiTech Part B: MAE 35.2 zero-shot · generalises without fine-tuning"),
        ("Sparse Routing",          "60.2% MAE reduction on sparse scenes · primary contribution of routing"),
    ]
    row_h20 = Inches(0.72)
    gap20   = Inches(0.04)
    cy20    = Inches(1.15)
    for badge, content in contributions:
        rect(s, Inches(0.35), cy20, Inches(2.0), row_h20, fill=BLUE)
        txt(s, badge,
            Inches(0.35), cy20 + Inches(0.17), Inches(2.0), Inches(0.38),
            size=11, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
        rect(s, Inches(2.4), cy20, Inches(10.55), row_h20, fill=CARD)
        txt(s, content,
            Inches(2.52), cy20 + Inches(0.17), Inches(10.3), Inches(0.38),
            size=12, color=WHITE)
        cy20 += row_h20 + gap20

    # future work
    rect(s, Inches(0.35), Inches(4.85), Inches(12.6), Inches(2.1), fill=CARD)
    txt(s, "Future Work",
        Inches(0.5), Inches(4.95), Inches(12.3), Inches(0.36),
        size=13, bold=True, color=BLUE)
    future_row1 = ["→ Jetson Nano benchmarking",
                   "→ INT8 quantization (2–4× speedup)",
                   "→ Confidence-aware fallback routing"]
    future_row2 = ["→ High-density 3rd path (>3,000)",
                   "→ Federated learning integration",
                   "→ Temporal smoothing for video"]
    for fi, future_row in enumerate([future_row1, future_row2]):
        fy20 = Inches(5.38) + Inches(0.38) * fi
        for fj, ftext in enumerate(future_row):
            txt(s, ftext,
                Inches(0.5) + Inches(4.2) * fj, fy20,
                Inches(4.1), Inches(0.36),
                size=12, color=BODY)

    # quote  — safe zone: y=6.85, height=0.28, bottom = 7.13 < 7.15
    rect(s, Inches(0.35), Inches(6.83), Inches(12.6), Inches(0.06), fill=BLUE)
    txt(s, '"A 4.35M-parameter system that beats models 4\u00d7 its size \u2014 through smart, learned routing."',
        Inches(0.35), Inches(6.9), Inches(12.6), Inches(0.28),
        size=13, bold=True, color=BLUE, align=PP_ALIGN.CENTER, italic=True)

    # ══════════════════════════════════════════════════════════════════════
    # SLIDE 21 — Q&A
    # ══════════════════════════════════════════════════════════════════════
    s = blank_slide(prs)
    bg(s)
    slide_title(s, "Thank You · Questions?")

    txt(s, "Q & A",
        Inches(0.35), Inches(1.8), Inches(12.6), Inches(1.2),
        size=72, bold=True, color=WHITE, align=PP_ALIGN.CENTER)

    stat_data21 = [
        (Inches(0.9),  "MAE 180.9",    "Best Result — NWPU-Crowd val"),
        (Inches(4.76), "4.35M params", "73.3% smaller than CSRNet"),
        (Inches(8.62), "−60.2%",       "Sparse routing gain"),
    ]
    for sx, val, lbl in stat_data21:
        rect(s, sx, Inches(3.8), Inches(3.8), Inches(1.35), fill=CARD2)
        txt(s, val,
            sx, Inches(4.0), Inches(3.8), Inches(0.55),
            size=26, bold=True, color=BLUE, align=PP_ALIGN.CENTER)
        txt(s, lbl,
            sx, Inches(4.65), Inches(3.8), Inches(0.38),
            size=11, color=MUTED, align=PP_ALIGN.CENTER)

    txt(s, "GitHub: Crowd-Density-Hybrid-Model · NWPU-Crowd + ShanghaiTech Part A & B · PyTorch 2.6",
        Inches(0.35), Inches(6.5), Inches(12.6), Inches(0.38),
        size=11, color=MUTED, align=PP_ALIGN.CENTER)

    # ── Save ───────────────────────────────────────────────────────────────
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), output)
    prs.save(out_path)
    print(f"Saved: {out_path}  ({len(prs.slides)} slides)")
    return out_path


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "thesis_presentation.pptx"
    build(out)
