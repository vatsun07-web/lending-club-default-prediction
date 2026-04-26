"""
build_pdf_report.py
────────────────────
Generates a polished, business-style PDF report for the LendingClub
Default Prediction project.

Run from project root:
    python build_pdf_report.py

Output: reports/lending_club_report.pdf
"""

import json, os, sys
from pathlib import Path
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle,
    Spacer, HRFlowable, PageBreak, Image as RLImage,
    KeepTogether
)
from reportlab.platypus.flowables import Flowable
from reportlab.pdfgen import canvas as pdfcanvas

# ── Page geometry ──────────────────────────────────────────────────────────────
W, H    = A4                          # 595.28 x 841.89 pts
ML = MR = 22*mm
MT = MB = 20*mm
CW = W - ML - MR                     # content width ≈ 151 mm

# ── Brand palette ──────────────────────────────────────────────────────────────
INK        = colors.HexColor("#0f172a")
INK_MID    = colors.HexColor("#1e293b")
INK_SOFT   = colors.HexColor("#334155")
SLATE      = colors.HexColor("#475569")
MUTED      = colors.HexColor("#94a3b8")
BORDER     = colors.HexColor("#e2e8f0")
SURFACE    = colors.HexColor("#f8fafc")
WHITE      = colors.white
AMBER      = colors.HexColor("#d97706")
AMBER_LT   = colors.HexColor("#fbbf24")
AMBER_BG   = colors.HexColor("#fffbeb")
TEAL       = colors.HexColor("#0d9488")
RED        = colors.HexColor("#dc2626")
GREEN      = colors.HexColor("#16a34a")
RED_BG     = colors.HexColor("#fee2e2")
GREEN_BG   = colors.HexColor("#dcfce7")
BLUE_BG    = colors.HexColor("#dbeafe")
YELLOW_BG  = colors.HexColor("#fef9c3")

# ── Load artifacts ─────────────────────────────────────────────────────────────
def load_json(path, fallback=None):
    try:
        with open(path) as f: return json.load(f)
    except FileNotFoundError:
        print(f"  [warn] {path} not found — using fallback")
        return fallback or {}

_EVAL_FALLBACK = {
    "metrics": {
        "roc_auc": 0.7117, "pr_auc": 0.3345, "recall": 0.8741,
        "precision": 0.2262, "f1": 0.3594,
    },
    "confusion_matrix": {"tn": 82774, "fp": 136084, "fn": 5731, "tp": 39781},
}
eval_results   = load_json("models/07_evaluation_results.json", _EVAL_FALLBACK)
grade_metrics  = load_json("models/07_grade_metrics.json", [])
threshold_data = load_json("models/06_threshold.json", {"optimal_threshold": 0.3592})

# Confusion matrix — saved as a dict with keys tn/fp/fn/tp (not a nested list)
_cm  = eval_results.get("confusion_matrix", _EVAL_FALLBACK["confusion_matrix"])
TN   = _cm.get("tn", 82774)
FP   = _cm.get("fp", 136084)
FN   = _cm.get("fn", 5731)
TP   = _cm.get("tp", 39781)

# Metrics — saved under a nested 'metrics' key
_metrics = eval_results.get("metrics", _EVAL_FALLBACK["metrics"])
roc   = _metrics.get("roc_auc",   0.7117)
prauc = _metrics.get("pr_auc",    0.3345)
rec   = _metrics.get("recall",    0.8741)
prec  = _metrics.get("precision", 0.2262)
f1    = _metrics.get("f1",        0.3594)

# Threshold — saved under 'optimal_threshold' (not 'threshold')
thr   = threshold_data.get("optimal_threshold", 0.3592)

losses_avoided  = TP  * 12_000
profit_foregone = FP  *  1_200
losses_incurred = FN  * 12_000
profit_earned   = TN  *  1_200
total_with      = losses_avoided - profit_foregone - losses_incurred + profit_earned
total_without   = -(TP+FN)*12_000 + (TN+FP)*1_200
net_advantage   = total_with - total_without

IMAGES = {
    "shap_bar":      "models/07_shap_bar.png",
    "shap_beeswarm": "models/07_shap_beeswarm.png",
    "waterfall_tp":  "models/07_shap_waterfall_tp.png",
    "waterfall_fn":  "models/07_shap_waterfall_fn.png",
    "score_dist":    "models/07_score_distribution.png",
    "roc":           "models/06_pr_roc_curves.png",
    "grade":         "models/07_grade_metrics.png",
}

def img_exists(key):
    return os.path.exists(IMAGES.get(key, ""))

# ══════════════════════════════════════════════════════════════════════════════
# CUSTOM FLOWABLES
# ══════════════════════════════════════════════════════════════════════════════

class ColorRect(Flowable):
    """Solid color rectangle — used for accent bars and dividers."""
    def __init__(self, w, h, fill_color=AMBER, radius=0):
        super().__init__()
        self.w = w; self.h = h
        self.fill_color = fill_color
        self.radius = radius
        self.width = w; self.height = h

    def draw(self):
        self.canv.setFillColor(self.fill_color)
        if self.radius:
            self.canv.roundRect(0, 0, self.w, self.h, self.radius, fill=1, stroke=0)
        else:
            self.canv.rect(0, 0, self.w, self.h, fill=1, stroke=0)

class MetricCard(Flowable):
    """Single KPI card with top accent bar."""
    def __init__(self, label, value, sub, bar_color=AMBER, w=None, h=None):
        super().__init__()
        self.label = label; self.value = value; self.sub = sub
        self.bar_color = bar_color
        self.width  = w or 85*mm
        self.height = h or 28*mm

    def draw(self):
        c = self.canv
        # Card background
        c.setFillColor(SURFACE)
        c.setStrokeColor(BORDER)
        c.setLineWidth(0.5)
        c.roundRect(0, 0, self.width, self.height, 3, fill=1, stroke=1)
        # Accent bar top
        c.setFillColor(self.bar_color)
        c.roundRect(0, self.height-3, self.width, 3, 1.5, fill=1, stroke=0)
        # Label
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 6.5)
        c.drawString(8, self.height-14, self.label.upper())
        # Value
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(8, self.height-30, self.value)
        # Sub text
        c.setFillColor(SLATE)
        c.setFont("Helvetica", 7)
        c.drawString(8, 7, self.sub)

class SectionHeader(Flowable):
    """Numbered section header with amber eyebrow."""
    def __init__(self, number, title, width=None):
        super().__init__()
        self.number = number; self.title = title
        self.width  = width or CW
        self.height = 22*mm

    def draw(self):
        c = self.canv
        # Amber rule top
        c.setFillColor(AMBER)
        c.rect(0, self.height-2, self.width, 2, fill=1, stroke=0)
        # Number eyebrow
        c.setFillColor(AMBER)
        c.setFont("Helvetica", 7)
        c.drawString(0, self.height-12, self.number)
        # Title
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(0, self.height-26, self.title)

class CalloutBox(Flowable):
    """Amber left-border callout with title and body text."""
    def __init__(self, title, body, width=None):
        super().__init__()
        self.title = title
        self.body  = body
        self.width = width or CW
        # Estimate height: 4pt title + wrapped body
        chars_per_line = int(self.width / 4.8)
        words = body.split()
        lines = 1; cur = 0
        for w in words:
            if cur + len(w) + 1 > chars_per_line:
                lines += 1; cur = len(w)
            else:
                cur += len(w) + 1
        self.height = 10*mm + lines * 4.5*mm + 6*mm

    def draw(self):
        c = self.canv
        c.setFillColor(AMBER_BG)
        c.roundRect(0, 0, self.width, self.height, 3, fill=1, stroke=0)
        c.setFillColor(AMBER)
        c.rect(0, 0, 3, self.height, fill=1, stroke=0)
        # Title
        c.setFillColor(AMBER)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(10, self.height-10, self.title.upper())
        # Body — simple word-wrap
        c.setFillColor(INK_SOFT)
        c.setFont("Helvetica", 8)
        max_w   = self.width - 18
        y       = self.height - 21
        words   = self.body.split()
        line    = ""
        for word in words:
            test = (line + " " + word).strip()
            if c.stringWidth(test, "Helvetica", 8) < max_w:
                line = test
            else:
                if y > 4:
                    c.drawString(10, y, line)
                y -= 11; line = word
        if line and y > 4:
            c.drawString(10, y, line)

class DarkCallout(Flowable):
    """Dark navy callout box — used for key findings."""
    def __init__(self, title, body, width=None):
        super().__init__()
        self.title = title; self.body = body
        self.width = width or CW
        chars_per_line = int((self.width-22) / 4.8)
        words = body.split(); lines=1; cur=0
        for w in words:
            if cur + len(w) + 1 > chars_per_line: lines+=1; cur=len(w)
            else: cur+=len(w)+1
        self.height = 12*mm + lines*4.5*mm + 8*mm

    def draw(self):
        c = self.canv
        c.setFillColor(INK_MID)
        c.roundRect(0, 0, self.width, self.height, 4, fill=1, stroke=0)
        c.setFillColor(AMBER)
        c.rect(0, 0, 3, self.height, fill=1, stroke=0)
        c.setFillColor(AMBER_LT)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(12, self.height-11, self.title.upper())
        c.setFillColor(colors.HexColor("#cbd5e1"))
        c.setFont("Helvetica", 8)
        max_w = self.width - 22; y = self.height-23
        words = self.body.split(); line=""
        for word in words:
            test = (line+" "+word).strip()
            if c.stringWidth(test, "Helvetica", 8) < max_w: line=test
            else:
                if y>5: c.drawString(12, y, line)
                y-=11; line=word
        if line and y>5: c.drawString(12, y, line)

class ImpactRow(Flowable):
    """Two-column impact row: + on left, - on right."""
    def __init__(self, left_label, left_val, right_label, right_val, width=None):
        super().__init__()
        self.width = width or CW
        self.height = 22*mm
        self.ll=left_label; self.lv=left_val
        self.rl=right_label; self.rv=right_val

    def draw(self):
        c = self.canv
        half = (self.width - 8) / 2
        # Left card (green)
        c.setFillColor(GREEN_BG)
        c.roundRect(0,0, half, self.height, 3, fill=1, stroke=0)
        c.setFillColor(GREEN)
        c.setFont("Helvetica", 6); c.drawString(8, self.height-10, self.ll.upper())
        c.setFont("Helvetica-Bold", 14); c.drawString(8, self.height-24, self.lv)
        # Right card (red)
        x2 = half+8
        c.setFillColor(RED_BG)
        c.roundRect(x2, 0, half, self.height, 3, fill=1, stroke=0)
        c.setFillColor(RED)
        c.setFont("Helvetica", 6); c.drawString(x2+8, self.height-10, self.rl.upper())
        c.setFont("Helvetica-Bold", 14); c.drawString(x2+8, self.height-24, self.rv)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE TEMPLATES (header/footer)
# ══════════════════════════════════════════════════════════════════════════════

class ReportCanvas(pdfcanvas.Canvas):
    """Adds running header + footer to every page except cover."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for i, state in enumerate(self._saved_page_states):
            self.__dict__.update(state)
            if i > 0:  # skip cover
                self._draw_header_footer(i+1, num_pages)
            super().showPage()
        super().save()

    def _draw_header_footer(self, page_num, total):
        self.saveState()
        # Header rule
        self.setStrokeColor(BORDER)
        self.setLineWidth(0.5)
        self.line(ML, H-15*mm, W-MR, H-15*mm)
        self.setFillColor(MUTED)
        self.setFont("Helvetica", 7)
        self.drawString(ML, H-12*mm, "LENDING CLUB DEFAULT PREDICTION")
        self.drawRightString(W-MR, H-12*mm, "PORTFOLIO REPORT")
        # Footer rule
        self.line(ML, MB+4*mm, W-MR, MB+4*mm)
        self.setFillColor(MUTED)
        self.setFont("Helvetica", 7)
        self.drawString(ML, MB+1*mm, f"Confidential · {datetime.now().strftime('%B %Y')}")
        self.drawRightString(W-MR, MB+1*mm, f"Page {page_num} of {total}")
        self.restoreState()


# ══════════════════════════════════════════════════════════════════════════════
# STYLES
# ══════════════════════════════════════════════════════════════════════════════

def make_styles():
    s = {}
    s['lead'] = ParagraphStyle("lead",
        fontName="Helvetica", fontSize=10, leading=15,
        textColor=SLATE, spaceAfter=10, alignment=TA_JUSTIFY)
    s['body'] = ParagraphStyle("body",
        fontName="Helvetica", fontSize=9, leading=13,
        textColor=INK_SOFT, spaceAfter=7, alignment=TA_JUSTIFY)
    s['body_bold'] = ParagraphStyle("body_bold",
        fontName="Helvetica-Bold", fontSize=9, leading=13,
        textColor=INK, spaceAfter=5)
    s['h3'] = ParagraphStyle("h3",
        fontName="Helvetica-Bold", fontSize=12, leading=16,
        textColor=INK, spaceBefore=14, spaceAfter=6)
    s['h4'] = ParagraphStyle("h4",
        fontName="Helvetica-Bold", fontSize=8, leading=11,
        textColor=AMBER, spaceBefore=10, spaceAfter=5)
    s['caption'] = ParagraphStyle("caption",
        fontName="Helvetica-Oblique", fontSize=7.5, leading=10,
        textColor=MUTED, spaceAfter=8, alignment=TA_CENTER)
    s['bullet'] = ParagraphStyle("bullet",
        fontName="Helvetica", fontSize=9, leading=13,
        textColor=INK_SOFT, spaceAfter=4,
        leftIndent=12, firstLineIndent=-12)
    s['mono'] = ParagraphStyle("mono",
        fontName="Courier", fontSize=8, leading=11,
        textColor=INK_SOFT)
    s['tbl_hdr'] = ParagraphStyle("tbl_hdr",
        fontName="Helvetica-Bold", fontSize=7.5, leading=10,
        textColor=WHITE, alignment=TA_LEFT)
    s['tbl_cell'] = ParagraphStyle("tbl_cell",
        fontName="Helvetica", fontSize=8, leading=11,
        textColor=INK_SOFT)
    s['tbl_cell_bold'] = ParagraphStyle("tbl_cell_bold",
        fontName="Helvetica-Bold", fontSize=8, leading=11,
        textColor=INK)
    return s

ST = make_styles()

def b(text): return f"<b>{text}</b>"
def it(text): return f"<i>{text}</i>"
def code(text): return f'<font name="Courier" size="8">{text}</font>'
def amber(text): return f'<font color="#d97706">{text}</font>'


# ══════════════════════════════════════════════════════════════════════════════
# TABLE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def styled_table(data, col_widths, row_heights=None,
                 header_bg=INK, stripe=True, highlight_rows=None):
    t = Table(data, colWidths=col_widths, rowHeights=row_heights)
    cmds = [
        ('BACKGROUND',   (0,0), (-1,0), header_bg),
        ('TEXTCOLOR',    (0,0), (-1,0), WHITE),
        ('FONTNAME',     (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',     (0,0), (-1,0), 7.5),
        ('BOTTOMPADDING',(0,0), (-1,0), 6),
        ('TOPPADDING',   (0,0), (-1,0), 6),
        ('FONTNAME',     (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE',     (0,1), (-1,-1), 8),
        ('TEXTCOLOR',    (0,1), (-1,-1), INK_SOFT),
        ('TOPPADDING',   (0,1), (-1,-1), 5),
        ('BOTTOMPADDING',(0,1), (-1,-1), 5),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[WHITE, SURFACE] if stripe else [WHITE]),
        ('GRID',         (0,0), (-1,-1), 0.4, BORDER),
        ('LINEBELOW',    (0,0), (-1,0), 1, AMBER),
        ('ALIGN',        (0,0), (-1,-1), 'LEFT'),
        ('VALIGN',       (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING',  (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]
    if highlight_rows:
        for r in highlight_rows:
            cmds.append(('BACKGROUND', (0,r), (-1,r), AMBER_BG))
            cmds.append(('FONTNAME',   (0,r), (-1,r), 'Helvetica-Bold'))
            cmds.append(('TEXTCOLOR',  (0,r), (-1,r), INK))
    t.setStyle(TableStyle(cmds))
    return t

def maybe_image(key, width=None, caption=None):
    """Return [Image, caption_para] if file exists, else placeholder paragraph."""
    items = []
    path = IMAGES.get(key, "")
    w = width or CW
    if os.path.exists(path):
        try:
            img = RLImage(path, width=w, height=w*0.55)
            img.hAlign = 'CENTER'
            items.append(img)
        except Exception as e:
            items.append(Paragraph(f"[Image unavailable: {e}]", ST['caption']))
    else:
        items.append(Paragraph(f"[{path} not found — run Stage 7 to generate]", ST['caption']))
    if caption:
        items.append(Paragraph(caption, ST['caption']))
    return items

def sp(n=4): return Spacer(1, n*mm)
def rule(color=BORDER): return HRFlowable(width=CW, thickness=0.5, color=color, spaceAfter=3*mm, spaceBefore=3*mm)


# ══════════════════════════════════════════════════════════════════════════════
# COVER PAGE
# ══════════════════════════════════════════════════════════════════════════════

def draw_cover(c, doc):
    """Draw the cover page directly onto the canvas."""
    # Full dark background
    c.setFillColor(INK)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # Amber accent strip left
    c.setFillColor(AMBER)
    c.rect(0, 0, 5, H, fill=1, stroke=0)

    # Decorative circle top-right
    c.setFillColor(colors.HexColor("#1e293b"))
    c.circle(W+20, H+20, 180, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#0f172a"))
    c.circle(W-10, H-10, 100, fill=1, stroke=0)

    # Eyebrow
    c.setFillColor(AMBER)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(22*mm, H-50*mm, "END-TO-END MACHINE LEARNING PORTFOLIO  ·  CRISP-DM")

    # Title
    c.setFillColor(WHITE)
    c.setFont("Helvetica-Bold", 34)
    c.drawString(22*mm, H-72*mm, "Predicting Loan")
    c.setFillColor(AMBER_LT)
    c.drawString(22*mm, H-90*mm, "Default Risk")
    c.setFillColor(WHITE)
    c.drawString(22*mm, H-108*mm, "at Origination")

    # Amber divider
    c.setFillColor(AMBER)
    c.rect(22*mm, H-116*mm, 40*mm, 2, fill=1, stroke=0)

    # Subtitle
    c.setFillColor(colors.HexColor("#94a3b8"))
    c.setFont("Helvetica", 10)
    subtitle = (
        "A complete machine learning pipeline applied to 2.26 million LendingClub"
    )
    subtitle2 = "loan records — from raw SQL to explainable XGBoost with business impact."
    c.drawString(22*mm, H-128*mm, subtitle)
    c.drawString(22*mm, H-140*mm, subtitle2)

    # KPI strip
    kpis = [
        (f"{rec:.0%}", "DEFAULT RECALL"),
        (f"{roc:.4f}", "ROC-AUC"),
        ("+$628M",     "NET VALUE (TEST SET)"),
        ("2.26M",      "LOAN RECORDS"),
    ]
    kpi_y = H - 180*mm
    kpi_x = 22*mm
    box_w = (W - 44*mm - 3*8*mm) / 4
    for i,(val,lbl) in enumerate(kpis):
        x = kpi_x + i*(box_w + 8*mm)
        c.setFillColor(colors.HexColor("#1e293b"))
        c.roundRect(x, kpi_y, box_w, 28*mm, 3, fill=1, stroke=0)
        c.setFillColor(AMBER)
        c.rect(x, kpi_y+25*mm, box_w, 2, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 18)
        c.drawString(x+6, kpi_y+13*mm, val)
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 6.5)
        c.drawString(x+6, kpi_y+5*mm, lbl)

    # Meta block
    meta_y = 60*mm
    c.setFillColor(colors.HexColor("#1e293b"))
    c.roundRect(22*mm, meta_y, CW, 38*mm, 3, fill=1, stroke=0)

    meta = [
        ("Dataset",     "LendingClub 2007–2016  ·  2.26M rows  ·  151 columns"),
        ("Model",       "XGBoost  ·  Optuna-tuned  ·  1,046 estimators"),
        ("Methodology", "CRISP-DM  ·  8 stages  ·  End-to-end pipeline"),
        ("Generated",   datetime.now().strftime("%B %d, %Y")),
    ]
    mx = 30*mm; my = meta_y + 30*mm
    for label, value in meta:
        c.setFillColor(AMBER)
        c.setFont("Helvetica-Bold", 7)
        c.drawString(mx, my, label.upper())
        c.setFillColor(colors.HexColor("#94a3b8"))
        c.setFont("Helvetica", 8)
        c.drawString(mx + 26*mm, my, value)
        my -= 8*mm

    # Portfolio badge
    c.setFillColor(colors.HexColor("#292524"))
    c.roundRect(W-60*mm, meta_y+12*mm, 38*mm, 14*mm, 2, fill=1, stroke=0)
    c.setFillColor(AMBER_LT)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString(W-41*mm, meta_y+17.5*mm, "PORTFOLIO REPORT")


# ══════════════════════════════════════════════════════════════════════════════
# BUILD STORY
# ══════════════════════════════════════════════════════════════════════════════

def build_story():
    story = []

    # ── SECTION 1 — EXECUTIVE SUMMARY ────────────────────────────────────────
    story.append(SectionHeader("01", "Executive Summary"))
    story.append(sp(2))
    story.append(Paragraph(
        "This report presents a complete, production-style machine learning pipeline built "
        "to predict which loans will default — before a single payment is made. The analysis "
        "covers 2.26 million LendingClub loans originated between 2007 and 2016, and culminates "
        "in a tuned classifier that catches <b>87.4% of defaults</b> while generating an estimated "
        "<b>+$628 million in net value</b> on the held-out test set of 264,370 loans.",
        ST['lead']))
    story.append(sp(2))

    # Metric cards row
    card_w = (CW - 3*4*mm) / 4
    metrics = [
        ("Recall",    f"{rec:.1%}", f"Target \u2265 80% \u2714", GREEN),
        ("ROC-AUC",   f"{roc:.4f}", "Target \u2265 0.80", RED),
        ("PR-AUC",    f"{prauc:.4f}", "Target \u2265 0.70", RED),
        ("Threshold", f"{thr:.4f}", "Optimised (not 0.50)", AMBER),
    ]
    card_row_data = [[MetricCard(l,v,s,b,w=card_w,h=26*mm) for l,v,s,b in metrics]]
    card_tbl = Table(card_row_data,
                     colWidths=[card_w]*4,
                     rowHeights=[26*mm])
    card_tbl.setStyle(TableStyle([
        ('ALIGN',(0,0),(-1,-1),'LEFT'),
        ('LEFTPADDING',(0,0),(-1,-1),0),
        ('RIGHTPADDING',(0,0),(-1,-1),4*mm),
        ('TOPPADDING',(0,0),(-1,-1),0),
        ('BOTTOMPADDING',(0,0),(-1,-1),0),
    ]))
    story.append(card_tbl)
    story.append(sp(4))

    story.append(DarkCallout(
        "Key Finding — Information Ceiling, Not Modelling Failure",
        "ROC-AUC and PR-AUC fell short of targets. 50 Bayesian optimisation trials "
        "produced only +0.0018 ROC-AUC improvement, confirming the bottleneck is the "
        "feature set, not hyperparameters. The dominant predictor, int_rate, is "
        "LendingClub's own compressed risk assessment. The model re-ranks what the "
        "lender already knows — it cannot beat information that was never collected."
    ))
    story.append(sp(4))

    # Benchmark table
    story.append(Paragraph("Performance Progression", ST['h3']))
    bench_data = [
        ["Stage", "Configuration", "ROC-AUC", "Recall", "Threshold"],
        ["Previous", "Prior attempt", "0.700", "0.700", "0.50"],
        ["Stage 5 · S1", "XGB — no weighting", "0.7095", "0.030", "0.50"],
        ["Stage 5 · S2", "XGB — class weighted", "0.7099", "0.660", "0.50"],
        ["Stage 5 · S3", "XGB — weighted + opt. threshold", "0.7099", "0.875", "0.358"],
        [f"Stage 6 Final", "XGB — Optuna tuned", f"{roc:.4f}", f"{rec:.4f}", f"{thr:.4f}"],
        ["Target (min)", "—", "\u2265 0.80", "\u2265 0.75", "—"],
    ]
    col_w = [22*mm, 62*mm, 20*mm, 18*mm, 20*mm]
    story.append(styled_table(bench_data, col_w, highlight_rows=[5], stripe=True))
    story.append(Paragraph(
        "Highlighted row = final model. The Recall jump from 3% (Step 1) to 87.5% (Step 3) "
        "required zero additional training — only class weighting and threshold optimisation.",
        ST['caption']))
    story.append(sp(2))

    story.append(CalloutBox(
        "Takeaway",
        "95% of the Recall improvement came from how we use the model, not from the model itself. "
        "This is the most important lesson from the imbalanced classification literature: "
        "threshold and weighting decisions matter as much as algorithm choice."
    ))

    # ── SECTION 2 — BUSINESS PROBLEM ─────────────────────────────────────────
    story.append(PageBreak())
    story.append(SectionHeader("02", "Business Problem"))
    story.append(sp(2))
    story.append(Paragraph(
        "Default prediction is not a symmetric problem. Missing a default costs an order of "
        "magnitude more than flagging a good loan — and this asymmetry shapes every decision "
        "in the pipeline.",
        ST['lead']))
    story.append(sp(3))

    story.append(ImpactRow(
        "False Negative — Miss a Default",  f"-$12,000 per loan",
        "False Positive — Flag a Good Loan", f"-$1,200 per loan",
        width=CW
    ))
    story.append(sp(2))
    story.append(Paragraph(
        "Assumptions: average loan $15,000 · Loss Given Default 80% · annual margin 8%.",
        ST['caption']))
    story.append(sp(3))

    story.append(Paragraph(
        "The <b>10:1 cost asymmetry</b> means the model can tolerate up to 10 false positives per "
        "true positive and still add net value. The actual ratio in the test set is 3.4:1 — "
        "well inside the profitable zone. This framing justifies three design choices:",
        ST['body']))

    bullets = [
        ("<b>Recall over Accuracy.</b> 83% accuracy is trivially achieved by predicting "
         "\"no default\" for everything. Recall measures what fraction of actual defaults "
         "the model catches — the metric that directly maps to avoided losses."),
        ("<b>PR-AUC as the primary ranking metric.</b> With a 17.22% default rate "
         "(4.8:1 imbalance), ROC-AUC overstates performance on the minority class. "
         "PR-AUC gives an honest picture of real-world utility."),
        ("<b>Threshold optimisation, not default 0.5.</b> Lowering the decision boundary "
         f"from 0.50 to {thr:.4f} raised Recall from 66% to 87.4% with no retraining. "
         "The threshold is a business decision, not a statistical one."),
    ]
    for b_text in bullets:
        story.append(Paragraph(f"\u2022  {b_text}", ST['bullet']))
        story.append(sp(1))

    story.append(sp(2))
    story.append(Paragraph("Target Variable", ST['h3']))
    tgt_data = [
        ["Label", "loan_status Values"],
        ["Default = 1", "Charged Off, Default, Late (31-120 days), Does not meet credit policy (Charged Off)"],
        ["Non-Default = 0", "Fully Paid, Current, In Grace Period, Late (16-30 days), Does not meet credit policy (Fully Paid), Issued"],
    ]
    story.append(styled_table(tgt_data, [30*mm, CW-30*mm]))
    story.append(sp(2))
    story.append(Paragraph(
        "After removing 2017-2018 vintages (immature labels, suppressed default rates), the "
        "canonical default rate is <b>17.22%</b> — not the misleading 12.9% seen in the raw dataset. "
        "This correction updated the class imbalance ratio from 6.8:1 to <b>4.8:1</b>, "
        "directly affecting the class weighting parameter in modeling.",
        ST['body']))

    # ── SECTION 3 — PIPELINE ─────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(SectionHeader("03", "Pipeline Overview"))
    story.append(sp(2))
    story.append(Paragraph(
        "Eight CRISP-DM stages, each saving artifacts consumed by the next. "
        "The pipeline is fully reproducible from raw SQL to final model.",
        ST['lead']))
    story.append(sp(3))

    stages = [
        ("00", "Business Understanding",
         "Defined cost framing (FN:FP 10:1), target variable, and a 77-column leakage "
         "audit before touching the data. Post-origination fields excluded upfront.",
         "leakage_columns.json · business_understanding.md"),
        ("01", "Exploratory Data Analysis",
         "Full 2.26M row dataset explored via SQL aggregates — peak memory 132 bytes. "
         "Grade monotonicity confirmed (A: 3.6% default to G: 40.0%). Temporal finding: "
         "2017-2018 vintages have immature labels.",
         "SQL-first · no pandas full load"),
        ("02", "Cleaning & Preprocessing",
         "Vintage filter removed 938,854 rows (41.5%), correcting the default rate to "
         "17.22%. 90 columns excluded. Target encoding for addr_state. Sentinel "
         "imputation for mths_since_recent_bc (no-card history = meaningful signal).",
         "02_cleaned.parquet · 1,321,847 rows · 81 cols · 84.6 MB"),
        ("03", "Feature Selection",
         "Four systematic passes: variance threshold (-8 features), Pearson correlation "
         "pruning (-6), effect size review (-0), domain judgment (-0). sub_grade dropped "
         "(r=0.978 with int_rate). 79 features narrowed to 65.",
         "03_selected_features.json · 65 features"),
        ("04", "Feature Engineering",
         "Five engineered features. Top two — fico_int_rate_gap (d=0.53) and risk_score "
         "(d=0.51) — rank among the strongest predictors in the full set. credit_age_months "
         "rescued from the dropped date column earliest_cr_line.",
         "04_engineered.parquet · 70 features entering modeling"),
        ("05", "Baseline Modeling",
         "Three sequential steps isolated contribution of each intervention: no weighting "
         "(Recall 3%), class weighted (66%), weighted + threshold optimised (87.5%). "
         "ROC-AUC was unchanged across all steps — confirming the information ceiling.",
         "XGBoost · scale_pos_weight=4.8 · threshold=0.3584"),
        ("06", "Hyperparameter Tuning",
         "50 Bayesian trials via Optuna. Best trial #44. ROC-AUC improvement: +0.0018. "
         "Near-zero gain confirmed the feature set as the binding constraint.",
         "Optuna · 50 trials · 1,046 estimators"),
        ("07", "Evaluation",
         "Full held-out test evaluation with SHAP explainability (5,000 stratified "
         "samples), calibration analysis, grade-level segmentation, and business "
         "impact quantification.",
         "SHAP · grade segmentation · +$628M business value"),
    ]

    for num, title, desc, tag in stages:
        row_data = [[
            Paragraph(f"<b>{num}</b>", ParagraphStyle("dot",
                fontName="Helvetica-Bold", fontSize=9, textColor=AMBER if num in ["04","05","06"] else MUTED)),
            Paragraph(f"<b>{title}</b><br/><font size='8' color='#475569'>{desc}</font>",
                ParagraphStyle("stage", fontName="Helvetica", fontSize=8.5,
                    leading=12, textColor=INK_SOFT, spaceAfter=2)),
            Paragraph(f"<font size='7' color='#94a3b8'>{tag}</font>",
                ParagraphStyle("tag", fontName="Courier", fontSize=7,
                    leading=10, textColor=MUTED)),
        ]]
        t = Table(row_data, colWidths=[10*mm, 95*mm, CW-105*mm])
        t.setStyle(TableStyle([
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('TOPPADDING',(0,0),(-1,-1),5),
            ('BOTTOMPADDING',(0,0),(-1,-1),5),
            ('LEFTPADDING',(0,0),(0,0),0),
            ('LINEBELOW',(0,0),(-1,-1),0.3,BORDER),
        ]))
        story.append(t)

    # ── SECTION 4 — MODEL RESULTS ─────────────────────────────────────────────
    story.append(PageBreak())
    story.append(SectionHeader("04", "Model Results"))
    story.append(sp(2))
    story.append(Paragraph(
        f"Performance on the held-out test set of 264,370 loans. "
        f"Decision threshold: {thr:.4f} (optimised on the PR curve, not default 0.50).",
        ST['lead']))
    story.append(sp(3))

    # Confusion matrix as styled table
    story.append(Paragraph("Confusion Matrix", ST['h3']))
    cm_data = [
        ["", "Predicted: No Default", "Predicted: Default"],
        ["Actual: No Default",
         Paragraph(f"<b><font color='#1d4ed8'>{TN:,}</font></b><br/><font size='7' color='#64748b'>True Negative — correct approvals</font>", ST['tbl_cell']),
         Paragraph(f"<b><font color='#854d0e'>{FP:,}</font></b><br/><font size='7' color='#64748b'>False Positive — rejected good loans</font>", ST['tbl_cell'])],
        ["Actual: Default",
         Paragraph(f"<b><font color='#b91c1c'>{FN:,}</font></b><br/><font size='7' color='#64748b'>False Negative — missed defaults</font>", ST['tbl_cell']),
         Paragraph(f"<b><font color='#15803d'>{TP:,}</font></b><br/><font size='7' color='#64748b'>True Positive — caught defaults</font>", ST['tbl_cell'])],
    ]
    cm_tbl = Table(cm_data, colWidths=[38*mm, 56*mm, 56*mm], rowHeights=[10*mm, 20*mm, 20*mm])
    cm_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), INK),
        ('TEXTCOLOR',  (0,0), (-1,0), WHITE),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,0), 7.5),
        ('BACKGROUND', (1,1), (1,1), BLUE_BG),
        ('BACKGROUND', (2,1), (2,1), YELLOW_BG),
        ('BACKGROUND', (1,2), (1,2), RED_BG),
        ('BACKGROUND', (2,2), (2,2), GREEN_BG),
        ('BACKGROUND', (0,1), (0,-1), SURFACE),
        ('FONTNAME',   (0,1), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,1), (0,-1), 8),
        ('TEXTCOLOR',  (0,1), (0,-1), INK),
        ('GRID',       (0,0), (-1,-1), 0.5, BORDER),
        ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('LEFTPADDING',(0,0),(-1,-1),8),
    ]))
    story.append(cm_tbl)
    story.append(sp(2))
    story.append(Paragraph(
        f"Of {TP+FN:,} actual defaults in the test set, the model catches {TP:,} ({rec:.1%}). "
        f"The {FP:,} false positives represent good loans incorrectly rejected. "
        f"At the assumed 10:1 cost ratio, the actual 3.4:1 FP:TP rate is strongly net-positive.",
        ST['body']))
    story.append(sp(3))

    # PR/ROC curve
    story.extend(maybe_image("roc", width=CW,
        caption="Fig 1. PR and ROC curves for the final tuned model. The PR curve area "
                "is limited by the 17.22% base rate — an inherent property of the prediction problem."))
    story.append(sp(3))

    # Grade table
    story.append(Paragraph("Performance by Loan Grade", ST['h3']))
    story.append(Paragraph(
        "Segmenting by grade reveals where the model is most and least useful.",
        ST['body']))
    story.append(sp(2))

    GRADE_FALLBACK = [
        ("A","38,496","5.29%","0.1518","0.1383","0.6711"),
        ("B","65,174","10.72%","0.6093","0.1535","0.6386"),
        ("C","81,086","17.38%","0.9200","0.1908","0.6322"),
        ("D","46,090","24.56%","0.9895","0.2504","0.6268"),
        ("E","23,861","30.85%","0.9966","0.3109","0.6317"),
        ("F","8,598","37.50%","0.9984","0.3760","0.6143"),
        ("G","1,065","46.67%","1.0000","0.4667","0.6113"),
    ]
    grade_data = [["Grade","N (test)","Default Rate","Recall","Precision","ROC-AUC"]]
    if grade_metrics and isinstance(grade_metrics, list):
        for r in grade_metrics:
            grade_data.append([
                r.get("Grade", ""),
                f"{r.get('N', 0):,}",
                r.get("Default Rate", ""),          # already formatted as "17.22%" string
                f"{r.get('Recall', 0):.4f}",
                f"{r.get('Precision', 0):.4f}",
                f"{r.get('ROC-AUC', 0):.4f}",
            ])
    else:
        for row in GRADE_FALLBACK:
            grade_data.append(list(row))

    col_w2 = [14*mm,24*mm,28*mm,22*mm,24*mm,24*mm]
    story.append(styled_table(grade_data, col_w2, highlight_rows=[4,5,6,7]))
    story.append(Paragraph(
        "Highlighted rows (D-G): Recall >= 0.99 — the model is most actionable for high-risk grades. "
        "Grade A Recall (15.2%) reflects genuine unpredictability of low-rate borrower defaults, "
        "not a modeling deficiency.",
        ST['caption']))

    story.extend(maybe_image("score_dist", width=CW,
        caption="Fig 2. Predicted probability distributions. Mean separation of 0.137 "
                "between default and non-default illustrates the distributional overlap "
                "underlying the ROC-AUC ceiling."))

    # ── SECTION 5 — EXPLAINABILITY ────────────────────────────────────────────
    story.append(PageBreak())
    story.append(SectionHeader("05", "Model Explainability"))
    story.append(sp(2))
    story.append(Paragraph(
        "SHAP (SHapley Additive exPlanations) values explain each individual prediction "
        "by measuring how much each feature shifted the outcome — grounded in cooperative "
        "game theory. Computed on a stratified 5,000-loan sample of the test set.",
        ST['lead']))
    story.append(sp(3))

    # SHAP importance inline bars
    story.append(Paragraph("Top 10 Features — Mean |SHAP| Value", ST['h3']))
    shap_features = [
        ("int_rate",              0.27618, "LendingClub's compressed risk pricing signal"),
        ("acc_open_past_24mths",  0.14511, "Recent account openings — credit stress indicator"),
        ("term",                  0.11536, "Loan term: 60-month loans default at 1.6x the rate"),
        ("fico_range_high",       0.10202, "Credit score at origination"),
        ("risk_score *",          0.09181, "Engineered composite risk index (Stage 4)"),
        ("loan_to_income *",      0.08061, "Loan amount / annual income (Stage 4)"),
        ("total_bc_limit",        0.06284, "Total bankcard credit limit"),
        ("home_ownership_RENT",   0.05800, "Renting vs owning — tenure instability"),
        ("mo_sin_old_rev_tl_op",  0.05608, "Months since oldest revolving account opened"),
        ("inq_last_6mths",        0.05305, "Hard credit inquiries — active credit seeking"),
    ]
    max_shap = 0.27618
    shap_tbl_data = [["#", "Feature", "Mean |SHAP|", "Contribution", "What It Measures"]]
    for i, (feat, val, desc) in enumerate(shap_features):
        bar_pct = val / max_shap
        bar_len = int(bar_pct * 18)
        bar_str = "\u2588" * bar_len + "\u2591" * (18 - bar_len)
        shap_tbl_data.append([
            str(i+1), feat, f"{val:.5f}",
            Paragraph(f'<font name="Courier" size="7" color="#d97706">{bar_str}</font>',
                      ParagraphStyle("bar", fontName="Courier", fontSize=7, leading=9)),
            Paragraph(f'<font size="7" color="#475569">{desc}</font>',
                      ParagraphStyle("desc", fontName="Helvetica", fontSize=7, leading=9)),
        ])
    shap_tbl = Table(shap_tbl_data, colWidths=[8*mm,32*mm,20*mm,24*mm,CW-84*mm])
    shap_tbl.setStyle(TableStyle([
        ('BACKGROUND',   (0,0),(-1,0), INK),
        ('TEXTCOLOR',    (0,0),(-1,0), WHITE),
        ('FONTNAME',     (0,0),(-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',     (0,0),(-1,0), 7.5),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[WHITE, SURFACE]),
        ('FONTNAME',     (0,1),(-1,-1), 'Helvetica'),
        ('FONTSIZE',     (0,1),(-1,-1), 8),
        ('TEXTCOLOR',    (0,1),(-1,-1), INK_SOFT),
        ('BACKGROUND',   (0,5),(1,6), AMBER_BG),
        ('GRID',         (0,0),(-1,-1), 0.3, BORDER),
        ('LINEBELOW',    (0,0),(-1,0), 1, AMBER),
        ('ALIGN',        (0,0),(0,-1), 'CENTER'),
        ('ALIGN',        (2,0),(2,-1), 'RIGHT'),
        ('VALIGN',       (0,0),(-1,-1), 'MIDDLE'),
        ('TOPPADDING',   (0,0),(-1,-1), 4),
        ('BOTTOMPADDING',(0,0),(-1,-1), 4),
        ('LEFTPADDING',  (0,0),(-1,-1), 6),
        ('RIGHTPADDING', (0,0),(-1,-1), 5),
    ]))
    story.append(shap_tbl)
    story.append(Paragraph("* Engineered features from Stage 4", ST['caption']))
    story.append(sp(2))

    story.append(CalloutBox(
        "Key Insight",
        "int_rate is 1.9x more impactful than the #2 feature and ~4x in XGBoost gain "
        "importance. Both engineered features (risk_score #5, loan_to_income #6) outperform "
        "many raw features, validating Stage 4's engineering pass. The surprise is "
        "acc_open_past_24mths at #2 — high recent account openings signal a borrower "
        "actively seeking credit, often a precursor to financial stress."
    ))
    story.append(sp(4))

    story.extend(maybe_image("shap_beeswarm", width=CW,
        caption="Fig 3. SHAP beeswarm plot. Each dot = one loan. Position = feature's contribution "
                "to default probability. Color = feature value (red = high, blue = low). "
                "Monotonic directions confirm expected relationships: higher int_rate and "
                "longer term increase default probability; higher FICO decreases it."))
    story.append(sp(3))

    # Individual predictions — side by side
    story.append(Paragraph("Individual Prediction Explanations", ST['h3']))
    story.append(Paragraph(
        "SHAP waterfall plots show exactly which features drove two contrasting predictions.",
        ST['body']))
    story.append(sp(2))

    half_w = (CW - 6*mm) / 2
    img_row = [[]]
    has_tp = os.path.exists(IMAGES["waterfall_tp"])
    has_fn = os.path.exists(IMAGES["waterfall_fn"])

    if has_tp and has_fn:
        tp_img = RLImage(IMAGES["waterfall_tp"], width=half_w, height=half_w*0.75)
        fn_img = RLImage(IMAGES["waterfall_fn"], width=half_w, height=half_w*0.75)
        tp_cap = Paragraph(
            "<b>True Positive (prob=0.930)</b><br/>"
            "int_rate=26.57%, 60-month term, risk_score=0.87, "
            "loan_to_income=0.44, FICO=704. Every feature aligns toward default — "
            "the model's confidence is well-founded.",
            ParagraphStyle("cap2", fontName="Helvetica", fontSize=7.5, leading=10,
                           textColor=MUTED, alignment=TA_CENTER, spaceAfter=0))
        fn_cap = Paragraph(
            "<b>False Negative (prob=0.358 vs threshold 0.359)</b><br/>"
            "int_rate=9.17%, 36-month, low debt burden, 12-year credit history. "
            "Looked creditworthy at origination — default likely caused by a "
            "post-origination event invisible in any application snapshot.",
            ParagraphStyle("cap2", fontName="Helvetica", fontSize=7.5, leading=10,
                           textColor=MUTED, alignment=TA_CENTER, spaceAfter=0))
        pair_tbl = Table(
            [[tp_img, fn_img], [tp_cap, fn_cap]],
            colWidths=[half_w, half_w],
            rowHeights=[half_w*0.75, None]
        )
        pair_tbl.setStyle(TableStyle([
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('ALIGN', (0,0),(-1,-1),'CENTER'),
            ('LEFTPADDING',(0,0),(-1,-1),0),
            ('RIGHTPADDING',(1,0),(1,-1),0),
            ('RIGHTPADDING',(0,0),(0,-1),3*mm),
            ('TOPPADDING',(0,0),(-1,-1),0),
            ('BOTTOMPADDING',(0,0),(-1,-1),4),
        ]))
        story.append(pair_tbl)
    else:
        story.extend(maybe_image("waterfall_tp", width=CW,
            caption="Fig 4. True Positive (prob=0.930) — all features align toward default."))
        story.extend(maybe_image("waterfall_fn", width=CW,
            caption="Fig 5. False Negative (prob=0.358, just below threshold) — looked creditworthy at origination."))

    # ── SECTION 6 — BUSINESS IMPACT ──────────────────────────────────────────
    story.append(PageBreak())
    story.append(SectionHeader("06", "Business Impact"))
    story.append(sp(2))
    story.append(Paragraph(
        "Translating model performance into financial outcomes using standard "
        "consumer lending assumptions: average loan $15,000, Loss Given Default 80%, "
        "annual profit margin 8%.",
        ST['lead']))
    story.append(sp(3))

    # Impact table
    impact_data = [
        ["Component", "Calculation", "Amount"],
        ["Losses avoided", f"TP {TP:,} x $12,000", f"+${losses_avoided:,.0f}"],
        ["Profit earned on approved loans", f"TN {TN:,} x $1,200", f"+${profit_earned:,.0f}"],
        ["Losses incurred from missed defaults", f"FN {FN:,} x $12,000", f"-${losses_incurred:,.0f}"],
        ["Profit foregone on rejected good loans", f"FP {FP:,} x $1,200", f"-${profit_foregone:,.0f}"],
        ["Total value WITH model", "", f"+${total_with:,.0f}"],
        ["Total value WITHOUT model (approve all)", "", f"${total_without:,.0f}"],
        ["NET MODEL ADVANTAGE", "", f"+${net_advantage:,.0f}"],
    ]
    impact_tbl = Table(impact_data, colWidths=[76*mm, 38*mm, 36*mm])
    impact_tbl.setStyle(TableStyle([
        ('BACKGROUND',   (0,0),(-1,0), INK),
        ('TEXTCOLOR',    (0,0),(-1,0), WHITE),
        ('FONTNAME',     (0,0),(-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',     (0,0),(-1,0), 7.5),
        ('ROWBACKGROUNDS',(0,1),(-1,6),[WHITE, SURFACE, WHITE, SURFACE, WHITE, SURFACE]),
        ('FONTNAME',     (0,1),(-1,6), 'Helvetica'),
        ('FONTSIZE',     (0,1),(-1,6), 8),
        ('TEXTCOLOR',    (0,1),(-1,6), INK_SOFT),
        ('BACKGROUND',   (0,7),(-1,7), INK_MID),
        ('TEXTCOLOR',    (0,7),(-1,7), WHITE),
        ('FONTNAME',     (0,7),(-1,7), 'Helvetica-Bold'),
        ('FONTSIZE',     (0,7),(-1,7), 9),
        ('GRID',         (0,0),(-1,-1), 0.4, BORDER),
        ('LINEBELOW',    (0,0),(-1,0), 1, AMBER),
        ('LINEABOVE',    (0,7),(-1,7), 1, AMBER),
        ('ALIGN',        (1,0),(-1,-1), 'RIGHT'),
        ('VALIGN',       (0,0),(-1,-1), 'MIDDLE'),
        ('TOPPADDING',   (0,0),(-1,-1), 6),
        ('BOTTOMPADDING',(0,0),(-1,-1), 6),
        ('LEFTPADDING',  (0,0),(-1,-1), 10),
        ('RIGHTPADDING', (0,0),(-1,-1), 8),
    ]))
    story.append(impact_tbl)
    story.append(sp(3))

    story.append(CalloutBox(
        "Break-Even Analysis",
        "At the assumed 10:1 FN:FP cost ratio, the model can tolerate up to 10 false "
        "positives per true positive and still add value. The actual ratio of 3.4:1 "
        "is well inside the profitable zone. Even under conservative assumptions "
        "(LGD=50%, margin=12%), the model remains strongly net-positive."
    ))
    story.append(sp(4))

    story.append(Paragraph("Grade-Level Business Value", ST['h3']))
    story.append(Paragraph(
        "The model is most actionable at the high-risk end of the portfolio. "
        "Grades D through G (24-47% default rates) achieve Recall above 99% — "
        "almost every default in these segments is caught. For a lender seeking "
        "to reduce losses, restricting origination in Grades E-G delivers the "
        "highest loss-avoidance return with the fewest false positives.",
        ST['body']))
    story.append(sp(2))

    segment_data = [
        ["Grade", "Default Rate", "Recall", "Actionability"],
        ["A", "5.29%", "15.2%", "Low — most defaults unpredictable at origination"],
        ["B", "10.72%", "60.9%", "Moderate — material signal, some misses"],
        ["C", "17.38%", "92.0%", "High — catches 9 in 10 defaults"],
        ["D", "24.56%", "98.9%", "Very High — near-complete default capture"],
        ["E-G", "31-47%", ">99.6%", "Highest — effectively all defaults caught"],
    ]
    story.append(styled_table(segment_data,
                              [16*mm, 26*mm, 20*mm, CW-62*mm],
                              highlight_rows=[4,5]))

    # ── SECTION 7 — LIMITATIONS ────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(SectionHeader("07", "Honest Limitations"))
    story.append(sp(2))
    story.append(Paragraph(
        "A rigorous analysis requires an honest accounting of what this model "
        "cannot do — and why.",
        ST['lead']))
    story.append(sp(3))

    limitations = [
        ("ROC-AUC and PR-AUC Below Target",
         f"ROC-AUC = {roc:.4f} (target >= 0.80). This is an information ceiling problem, not a "
         "modelling failure. The dominant predictor, int_rate, is LendingClub's own pricing signal. "
         "The model largely re-ranks what the lender already knows. Beating 0.80 would require "
         "external data (bureau tradelines, bank transactions) not present in this dataset."),
        ("Calibration — Scores Are Not Probabilities",
         "XGBoost trained with class weighting produces shifted probability estimates. "
         "A loan scoring 0.60 does not have a 60% empirical default rate. Scores should be "
         "used as relative risk rankings only. Platt scaling or isotonic regression would "
         "be required before using outputs for risk pricing or regulatory capital."),
        ("Grade A Recall = 15.2%",
         "The model misses 85% of Grade A defaults. These borrowers present with low rates, "
         "strong FICO scores, and clean credit histories — statistically indistinguishable from "
         "non-defaulters. Grade A defaults are overwhelmingly caused by post-origination shocks "
         "(job loss, medical emergency) that no application-time model can predict."),
        ("Vintage Scope — 2007-2016 Only",
         "Training excludes recent macroeconomic regimes: COVID-era payment behaviour, "
         "2022-2023 rate environment, post-pandemic employment patterns. Model performance "
         "on loans originated after 2016 is unknown and may be degraded."),
        ("Business Impact Assumptions",
         "The +$628M estimate assumes LGD=80% and margin=8% — reasonable industry estimates "
         "but not verified against LendingClub financials. Regulatory constraints (ECOA fair "
         "lending), model risk management requirements, and application volume effects "
         "are not captured in this analysis."),
    ]
    for i, (title, body) in enumerate(limitations, 1):
        lim_data = [[
            Paragraph(f"<font color='#e2e8f0'><b>0{i}</b></font>",
                ParagraphStyle("n", fontName="Helvetica-Bold", fontSize=20, textColor=BORDER)),
            [Paragraph(f"<b>{title}</b>",
                ParagraphStyle("lt", fontName="Helvetica-Bold", fontSize=9.5,
                    textColor=INK, spaceAfter=4)),
             Paragraph(body, ST['body'])],
        ]]
        lt = Table(lim_data, colWidths=[14*mm, CW-14*mm])
        lt.setStyle(TableStyle([
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('TOPPADDING',(0,0),(-1,-1),8),
            ('BOTTOMPADDING',(0,0),(-1,-1),8),
            ('LEFTPADDING',(0,0),(0,0),0),
            ('LEFTPADDING',(1,0),(1,-1),6),
            ('LINEBELOW',(0,0),(-1,-1),0.3,BORDER),
        ]))
        story.append(lt)

    # ── SECTION 8 — FUTURE WORK ────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(SectionHeader("08", "Future Work"))
    story.append(sp(2))
    story.append(Paragraph(
        "The highest-leverage improvements for a production deployment, "
        "ranked by expected ROI.",
        ST['lead']))
    story.append(sp(3))

    # Column widths must sum to CW (≈151 mm).
    # Plain strings do NOT word-wrap in ReportLab tables — wrap every cell
    # in a Paragraph so long text flows across multiple lines instead of
    # overflowing into adjacent columns.
    _fw_num  = ParagraphStyle("fw_num",  fontName="Helvetica-Bold", fontSize=8,
                               leading=11, textColor=INK,      alignment=TA_CENTER)
    _fw_imp  = ParagraphStyle("fw_imp",  fontName="Helvetica",      fontSize=8,
                               leading=12, textColor=INK_SOFT)
    _fw_eff  = ParagraphStyle("fw_eff",  fontName="Helvetica",      fontSize=8,
                               leading=11, textColor=INK_SOFT,  alignment=TA_CENTER)
    _fw_imp2 = ParagraphStyle("fw_imp2", fontName="Helvetica",      fontSize=8,
                               leading=12, textColor=INK_SOFT)

    # col widths: # | Improvement | Effort | Expected Impact  — total = CW
    _fw_cols = [8*mm, 62*mm, 16*mm, CW - 86*mm]   # 8+62+16+65 = 151 mm

    def _fw_row(num, improvement, effort, impact):
        return [
            Paragraph(num,         _fw_num),
            Paragraph(improvement, _fw_imp),
            Paragraph(effort,      _fw_eff),
            Paragraph(impact,      _fw_imp2),
        ]

    fw_data = [
        # Header row — plain strings are fine here (styled_table sets its own font)
        ["#", "Improvement", "Effort", "Expected Impact"],
        _fw_row("1",
                "Calibration post-processing — Platt scaling or isotonic regression",
                "Low",
                "Enables probability interpretation; required for regulatory use"),
        _fw_row("2",
                "Separate Grade A model — features focused on employment stability "
                "and macro exposure rather than credit utilisation",
                "Medium",
                "Targeted Recall improvement for most unpredictable segment"),
        _fw_row("3",
                "Monotonic constraints on int_rate and fico_range_high in XGBoost",
                "Low",
                "Prevents overfitting artifacts; improves stakeholder trust"),
        _fw_row("4",
                "LightGBM comparison — 3-10x faster training, often comparable performance",
                "Medium",
                "Production retraining latency; marginal performance gain"),
        _fw_row("5",
                "Segment-specific thresholds — grade-level optimal cutoffs",
                "Low",
                "Better Precision/Recall trade-off per grade with no retraining"),
        _fw_row("6",
                "Behavioural features — payment history, utilisation trajectory",
                "High",
                "Breaks the information ceiling; fundamentally different problem"),
    ]
    story.append(styled_table(fw_data, _fw_cols, highlight_rows=[1, 3, 5]))
    story.append(sp(4))

    # Final callout
    story.append(DarkCallout(
        "Closing Thought",
        "The gap between a 0.71 ROC-AUC and a 0.80 target is not a failure of technique "
        "— it is a discovery about the limits of information available at loan origination. "
        "The model demonstrates that class weighting, threshold optimisation, and careful "
        "feature engineering can extract nearly all available signal from the data. "
        "Closing the remaining gap requires better data, not better algorithms."
    ))

    return story


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    out_dir = Path("reports")
    out_dir.mkdir(exist_ok=True)
    out_path = str(out_dir / "lending_club_report.pdf")

    doc = SimpleDocTemplate(
        out_path,
        pagesize=A4,
        leftMargin=ML, rightMargin=MR,
        topMargin=28*mm, bottomMargin=MB,
        title="LendingClub Default Prediction — Portfolio Report",
        author="Portfolio Report",
        subject="Machine Learning · CRISP-DM · XGBoost",
    )

    # Cover page drawn via canvas callback
    def add_cover(canvas, doc):
        if doc.page == 1:
            draw_cover(canvas, doc)

    story = build_story()

    # Insert cover as first element (blank placeholder that triggers the callback)
    from reportlab.platypus import FrameBreak
    cover_placeholder = PageBreak()

    print("Building PDF...")
    try:
        doc.build(
            [cover_placeholder] + story,
            onFirstPage=add_cover,
            canvasmaker=ReportCanvas,
        )
        size_kb = Path(out_path).stat().st_size / 1024
        print(f"\n  PDF generated: {out_path}")
        print(f"  Size: {size_kb:.0f} KB")
        print(f"  Pages: check the file to confirm\n")
    except Exception as e:
        print(f"\n  Error during build: {e}")
        import traceback; traceback.print_exc()
        sys.exit(1)
