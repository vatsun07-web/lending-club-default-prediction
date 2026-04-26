"""
generate_report.py
──────────────────
Generates a polished HTML portfolio report for the LendingClub
Default Prediction project. Run from the project root:

    python generate_report.py

Output: reports/lending_club_report.html
Open in Chrome → File → Print → Save as PDF
"""

import json
import base64
import os
from pathlib import Path
from datetime import datetime

# ── Load artifacts ─────────────────────────────────────────────────────────────
def load_json(path, fallback=None):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"  [warn] {path} not found — using fallback values")
        return fallback or {}

eval_results    = load_json("models/07_evaluation_results.json", {
    "roc_auc": 0.7117, "pr_auc": 0.3345, "recall": 0.8741,
    "precision": 0.2262, "f1": 0.3594,
    "confusion_matrix": [[82774, 136084], [5731, 39781]]
})
grade_metrics   = load_json("models/07_grade_metrics.json", [])
threshold_data  = load_json("models/06_threshold.json", {"threshold": 0.3592})
best_params     = load_json("models/06_best_params.json", {})

# ── Derived numbers ────────────────────────────────────────────────────────────
cm   = eval_results.get("confusion_matrix", [[82774, 136084], [5731, 39781]])
TN   = cm[0][0]; FP = cm[0][1]; FN = cm[1][0]; TP = cm[1][1]

losses_avoided  = TP  * 12_000
profit_foregone = FP  *  1_200
losses_incurred = FN  * 12_000
profit_earned   = TN  *  1_200
total_with      = losses_avoided - profit_foregone - losses_incurred + profit_earned
total_without   = -(TP + FN) * 12_000 + (TN + FP) * 1_200
net_advantage   = total_with - total_without

roc   = eval_results.get("roc_auc",   0.7117)
prauc = eval_results.get("pr_auc",    0.3345)
rec   = eval_results.get("recall",    0.8741)
prec  = eval_results.get("precision", 0.2262)
f1    = eval_results.get("f1",        0.3594)
thr   = threshold_data.get("threshold", 0.3592)

# ── Embed images as base64 ─────────────────────────────────────────────────────
def embed_image(path):
    try:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return f"data:image/png;base64,{data}"
    except FileNotFoundError:
        # Return a grey placeholder SVG
        svg = '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="400"><rect width="100%" height="100%" fill="#1e293b"/><text x="50%" y="50%" fill="#475569" font-family="monospace" font-size="14" text-anchor="middle" dy=".3em">Image not found: ' + path + '</text></svg>'
        b64 = base64.b64encode(svg.encode()).decode()
        return f"data:image/svg+xml;base64,{b64}"

img_shap_bar       = embed_image("models/07_shap_bar.png")
img_shap_beeswarm  = embed_image("models/07_shap_beeswarm.png")
img_waterfall_tp   = embed_image("models/07_shap_waterfall_tp.png")
img_waterfall_fn   = embed_image("models/07_shap_waterfall_fn.png")
img_score_dist     = embed_image("models/07_score_distribution.png")
img_calibration    = embed_image("models/07_calibration.png")
img_grade          = embed_image("models/07_grade_metrics.png")
img_roc            = embed_image("models/06_pr_roc_curves.png")
img_cm             = embed_image("models/06_confusion_matrix.png")

# ── Grade table rows ───────────────────────────────────────────────────────────
def grade_rows():
    HARDCODED = [
        ("A", "38,496",  "5.29%",  "0.1518", "0.1383", "0.6711"),
        ("B", "65,174",  "10.72%", "0.6093", "0.1535", "0.6386"),
        ("C", "81,086",  "17.38%", "0.9200", "0.1908", "0.6322"),
        ("D", "46,090",  "24.56%", "0.9895", "0.2504", "0.6268"),
        ("E", "23,861",  "30.85%", "0.9966", "0.3109", "0.6317"),
        ("F",  "8,598",  "37.50%", "0.9984", "0.3760", "0.6143"),
        ("G",  "1,065",  "46.67%", "1.0000", "0.4667", "0.6113"),
    ]
    if grade_metrics and isinstance(grade_metrics, list) and len(grade_metrics) > 0:
        rows = grade_metrics
    else:
        rows = None

    html = ""
    data = rows if rows else HARDCODED
    for i, row in enumerate(data):
        cls = "highlight-row" if i >= 3 else ""
        if rows:
            g    = row.get("grade", "")
            n    = f"{row.get('n', 0):,}"
            dr   = f"{row.get('default_rate', 0):.2%}"
            rcl  = f"{row.get('recall', 0):.4f}"
            prc  = f"{row.get('precision', 0):.4f}"
            rauc = f"{row.get('roc_auc', 0):.4f}"
        else:
            g, n, dr, rcl, prc, rauc = row
        html += f'<tr class="{cls}"><td><span class="grade-badge grade-{g}">{g}</span></td><td>{n}</td><td>{dr}</td><td>{rcl}</td><td>{prc}</td><td>{rauc}</td></tr>\n'
    return html

# ── HTML template ──────────────────────────────────────────────────────────────
HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LendingClub Default Prediction — Portfolio Report</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700;900&family=DM+Sans:wght@300;400;500&family=DM+Mono:wght@400;500&display=swap" rel="stylesheet">

<style>
/* ── Reset & base ────────────────────────────────────────────────────── */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

:root {{
  --ink:        #0f172a;
  --ink-mid:    #1e293b;
  --ink-soft:   #334155;
  --slate:      #475569;
  --muted:      #94a3b8;
  --border:     #e2e8f0;
  --surface:    #f8fafc;
  --white:      #ffffff;
  --amber:      #d97706;
  --amber-lt:   #fbbf24;
  --amber-bg:   #fffbeb;
  --teal:       #0d9488;
  --red:        #dc2626;
  --green:      #16a34a;
  --page-w:     860px;
}}

html {{ font-size: 15px; }}
body {{
  font-family: 'DM Sans', sans-serif;
  font-weight: 400;
  color: var(--ink);
  background: var(--white);
  line-height: 1.7;
}}

/* ── Print ───────────────────────────────────────────────────────────── */
@media print {{
  body {{ font-size: 13px; }}
  .page-break {{ page-break-before: always; }}
  .no-print {{ display: none !important; }}
  a {{ color: inherit; text-decoration: none; }}
  .cover {{ min-height: 100vh; }}
}}

/* ── Layout wrapper ──────────────────────────────────────────────────── */
.container {{
  max-width: var(--page-w);
  margin: 0 auto;
  padding: 0 40px;
}}

/* ════════════════════════════════════════════════════════════════════════
   COVER PAGE
   ════════════════════════════════════════════════════════════════════════ */
.cover {{
  min-height: 100vh;
  background: var(--ink);
  color: var(--white);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 64px 72px;
  position: relative;
  overflow: hidden;
}}

.cover::before {{
  content: '';
  position: absolute;
  top: -120px; right: -120px;
  width: 560px; height: 560px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(217,119,6,0.18) 0%, transparent 70%);
  pointer-events: none;
}}
.cover::after {{
  content: '';
  position: absolute;
  bottom: -80px; left: -80px;
  width: 400px; height: 400px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(13,148,136,0.12) 0%, transparent 70%);
  pointer-events: none;
}}

.cover-eyebrow {{
  font-family: 'DM Mono', monospace;
  font-size: 0.72rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--amber-lt);
  margin-bottom: 24px;
}}

.cover-title {{
  font-family: 'Playfair Display', serif;
  font-size: 3.6rem;
  font-weight: 900;
  line-height: 1.08;
  letter-spacing: -0.02em;
  max-width: 680px;
  margin-bottom: 20px;
}}

.cover-title em {{
  font-style: italic;
  color: var(--amber-lt);
}}

.cover-subtitle {{
  font-size: 1.05rem;
  color: #94a3b8;
  font-weight: 300;
  max-width: 520px;
  line-height: 1.6;
}}

.cover-divider {{
  width: 56px;
  height: 3px;
  background: var(--amber);
  margin: 36px 0;
}}

.cover-metrics {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 32px;
  margin-top: 24px;
}}

.cover-metric {{
  border-left: 2px solid rgba(217,119,6,0.5);
  padding-left: 16px;
}}

.cover-metric-value {{
  font-family: 'Playfair Display', serif;
  font-size: 2rem;
  font-weight: 700;
  color: var(--white);
  line-height: 1;
  margin-bottom: 4px;
}}

.cover-metric-label {{
  font-family: 'DM Mono', monospace;
  font-size: 0.68rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
}}

.cover-footer {{
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  padding-top: 48px;
  border-top: 1px solid rgba(255,255,255,0.1);
}}

.cover-meta {{
  font-family: 'DM Mono', monospace;
  font-size: 0.72rem;
  color: #64748b;
  line-height: 2;
}}

.cover-badge {{
  background: rgba(217,119,6,0.15);
  border: 1px solid rgba(217,119,6,0.4);
  color: var(--amber-lt);
  padding: 6px 14px;
  font-family: 'DM Mono', monospace;
  font-size: 0.68rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  border-radius: 2px;
}}

/* ════════════════════════════════════════════════════════════════════════
   SECTION HEADERS
   ════════════════════════════════════════════════════════════════════════ */
.section {{
  padding: 72px 0 48px;
}}
.section + .section {{
  border-top: 1px solid var(--border);
}}

.section-num {{
  font-family: 'DM Mono', monospace;
  font-size: 0.68rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--amber);
  margin-bottom: 10px;
}}

.section-title {{
  font-family: 'Playfair Display', serif;
  font-size: 2.1rem;
  font-weight: 700;
  line-height: 1.15;
  letter-spacing: -0.01em;
  color: var(--ink);
  margin-bottom: 8px;
}}

.section-lead {{
  font-size: 1.05rem;
  color: var(--slate);
  font-weight: 300;
  max-width: 640px;
  margin-bottom: 40px;
  line-height: 1.65;
}}

/* ════════════════════════════════════════════════════════════════════════
   METRIC CARDS
   ════════════════════════════════════════════════════════════════════════ */
.metric-grid {{
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin: 32px 0;
}}
.metric-grid-5 {{
  grid-template-columns: repeat(5, 1fr);
}}

.metric-card {{
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 24px 20px;
  position: relative;
  overflow: hidden;
}}

.metric-card::before {{
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: var(--ink-soft);
}}

.metric-card.status-pass::before  {{ background: var(--green); }}
.metric-card.status-fail::before  {{ background: var(--red); }}
.metric-card.status-amber::before {{ background: var(--amber); }}

.metric-value {{
  font-family: 'Playfair Display', serif;
  font-size: 2.2rem;
  font-weight: 700;
  line-height: 1;
  color: var(--ink);
  margin-bottom: 6px;
}}
.metric-card.status-pass .metric-value {{ color: var(--green); }}
.metric-card.status-fail .metric-value {{ color: var(--red); }}

.metric-label {{
  font-family: 'DM Mono', monospace;
  font-size: 0.68rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 8px;
}}

.metric-target {{
  font-size: 0.78rem;
  color: var(--slate);
}}

.metric-badge {{
  display: inline-block;
  margin-top: 8px;
  padding: 2px 8px;
  border-radius: 2px;
  font-family: 'DM Mono', monospace;
  font-size: 0.65rem;
  letter-spacing: 0.06em;
}}
.badge-pass  {{ background: #dcfce7; color: #15803d; }}
.badge-fail  {{ background: #fee2e2; color: #b91c1c; }}
.badge-note  {{ background: #f1f5f9; color: var(--slate); }}

/* ════════════════════════════════════════════════════════════════════════
   CALLOUT BOXES
   ════════════════════════════════════════════════════════════════════════ */
.callout {{
  background: var(--amber-bg);
  border-left: 4px solid var(--amber);
  padding: 20px 24px;
  margin: 28px 0;
  border-radius: 0 6px 6px 0;
}}
.callout-title {{
  font-family: 'DM Mono', monospace;
  font-size: 0.7rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--amber);
  margin-bottom: 6px;
}}
.callout p {{
  font-size: 0.9rem;
  color: var(--ink-soft);
  line-height: 1.6;
}}

.callout-dark {{
  background: var(--ink);
  border-left: 4px solid var(--amber);
  color: var(--white);
  padding: 28px 32px;
  border-radius: 0 8px 8px 0;
  margin: 32px 0;
}}
.callout-dark .callout-title {{ color: var(--amber-lt); }}
.callout-dark p {{
  color: #cbd5e1;
  font-size: 0.95rem;
  line-height: 1.7;
}}
.callout-dark strong {{ color: var(--white); }}

/* ════════════════════════════════════════════════════════════════════════
   TABLES
   ════════════════════════════════════════════════════════════════════════ */
.table-wrap {{
  overflow-x: auto;
  margin: 28px 0;
  border: 1px solid var(--border);
  border-radius: 8px;
}}

table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}}

thead {{
  background: var(--ink);
  color: var(--white);
}}

thead th {{
  padding: 13px 16px;
  font-family: 'DM Mono', monospace;
  font-size: 0.65rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  font-weight: 500;
  text-align: left;
}}

tbody tr {{
  border-bottom: 1px solid var(--border);
  transition: background 0.15s;
}}
tbody tr:last-child {{ border-bottom: none; }}
tbody tr:hover {{ background: var(--surface); }}
tbody tr.highlight-row {{ background: #fffbeb; }}
tbody tr.highlight-row:hover {{ background: #fef3c7; }}

tbody td {{
  padding: 11px 16px;
  color: var(--ink-soft);
}}

tbody td:first-child {{
  font-weight: 500;
  color: var(--ink);
}}

/* ════════════════════════════════════════════════════════════════════════
   PIPELINE TIMELINE
   ════════════════════════════════════════════════════════════════════════ */
.pipeline {{
  display: flex;
  flex-direction: column;
  gap: 0;
  margin: 36px 0;
  position: relative;
}}
.pipeline::before {{
  content: '';
  position: absolute;
  left: 22px; top: 28px; bottom: 28px;
  width: 2px;
  background: linear-gradient(to bottom, var(--border), var(--amber), var(--border));
}}

.pipeline-stage {{
  display: flex;
  gap: 24px;
  padding: 20px 0;
  align-items: flex-start;
}}

.pipeline-dot {{
  width: 46px;
  height: 46px;
  border-radius: 50%;
  background: var(--ink);
  border: 2px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'DM Mono', monospace;
  font-size: 0.7rem;
  font-weight: 500;
  color: var(--muted);
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}}
.pipeline-dot.active {{
  background: var(--amber);
  border-color: var(--amber);
  color: var(--ink);
  font-weight: 700;
}}

.pipeline-body {{
  padding-top: 10px;
  flex: 1;
}}

.pipeline-stage-title {{
  font-family: 'Playfair Display', serif;
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 4px;
}}

.pipeline-stage-desc {{
  font-size: 0.875rem;
  color: var(--slate);
  line-height: 1.6;
}}

.pipeline-stage-tag {{
  display: inline-block;
  margin-top: 6px;
  padding: 2px 8px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 2px;
  font-family: 'DM Mono', monospace;
  font-size: 0.65rem;
  letter-spacing: 0.05em;
  color: var(--slate);
}}

/* ════════════════════════════════════════════════════════════════════════
   IMAGES
   ════════════════════════════════════════════════════════════════════════ */
.fig {{
  margin: 32px 0;
}}
.fig img {{
  width: 100%;
  border: 1px solid var(--border);
  border-radius: 8px;
  display: block;
}}
.fig-caption {{
  margin-top: 10px;
  font-size: 0.82rem;
  color: var(--muted);
  font-style: italic;
  text-align: center;
  line-height: 1.5;
}}
.fig-caption strong {{
  font-style: normal;
  color: var(--slate);
}}

.fig-row {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin: 32px 0;
}}

/* ════════════════════════════════════════════════════════════════════════
   IMPACT BLOCK
   ════════════════════════════════════════════════════════════════════════ */
.impact-grid {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin: 32px 0;
}}

.impact-card {{
  padding: 28px;
  border-radius: 8px;
  border: 1px solid var(--border);
}}

.impact-card.positive {{
  background: #f0fdf4;
  border-color: #bbf7d0;
}}
.impact-card.negative {{
  background: #fff1f2;
  border-color: #fecdd3;
}}

.impact-card-label {{
  font-family: 'DM Mono', monospace;
  font-size: 0.65rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-bottom: 8px;
}}
.impact-card.positive .impact-card-label {{ color: #15803d; }}
.impact-card.negative .impact-card-label {{ color: #b91c1c; }}

.impact-card-value {{
  font-family: 'Playfair Display', serif;
  font-size: 1.9rem;
  font-weight: 700;
  line-height: 1;
  margin-bottom: 6px;
}}
.impact-card.positive .impact-card-value {{ color: #15803d; }}
.impact-card.negative .impact-card-value {{ color: #b91c1c; }}

.impact-card-desc {{
  font-size: 0.82rem;
  color: var(--slate);
}}

.impact-total {{
  margin-top: 24px;
  padding: 32px;
  background: var(--ink);
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}}
.impact-total-label {{
  font-family: 'DM Mono', monospace;
  font-size: 0.75rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 6px;
}}
.impact-total-value {{
  font-family: 'Playfair Display', serif;
  font-size: 2.8rem;
  font-weight: 700;
  color: var(--amber-lt);
  line-height: 1;
}}
.impact-total-sub {{
  font-size: 0.85rem;
  color: #64748b;
  margin-top: 8px;
}}

/* ════════════════════════════════════════════════════════════════════════
   LIMITATIONS
   ════════════════════════════════════════════════════════════════════════ */
.limitation {{
  display: flex;
  gap: 20px;
  padding: 24px 0;
  border-bottom: 1px solid var(--border);
}}
.limitation:last-child {{ border-bottom: none; }}

.limitation-num {{
  font-family: 'Playfair Display', serif;
  font-size: 2rem;
  font-weight: 700;
  color: var(--border);
  line-height: 1;
  flex-shrink: 0;
  width: 40px;
}}

.limitation-title {{
  font-family: 'Playfair Display', serif;
  font-size: 1rem;
  font-weight: 600;
  color: var(--ink);
  margin-bottom: 6px;
}}

.limitation-body {{
  font-size: 0.875rem;
  color: var(--slate);
  line-height: 1.65;
}}

/* ════════════════════════════════════════════════════════════════════════
   GRADE BADGES
   ════════════════════════════════════════════════════════════════════════ */
.grade-badge {{
  display: inline-block;
  width: 26px; height: 26px;
  border-radius: 50%;
  font-family: 'DM Mono', monospace;
  font-size: 0.72rem;
  font-weight: 500;
  text-align: center;
  line-height: 26px;
  color: white;
}}
.grade-A {{ background: #16a34a; }}
.grade-B {{ background: #65a30d; }}
.grade-C {{ background: #ca8a04; }}
.grade-D {{ background: #d97706; }}
.grade-E {{ background: #ea580c; }}
.grade-F {{ background: #dc2626; }}
.grade-G {{ background: #9b1c1c; }}

/* ════════════════════════════════════════════════════════════════════════
   BENCHMARK TABLE HIGHLIGHT
   ════════════════════════════════════════════════════════════════════════ */
tr.final-row td {{
  background: #fffbeb !important;
  font-weight: 500;
  color: var(--ink) !important;
}}
tr.target-row td {{
  background: var(--surface);
  font-style: italic;
  color: var(--muted) !important;
  font-family: 'DM Mono', monospace;
  font-size: 0.78rem;
}}

/* ════════════════════════════════════════════════════════════════════════
   CONFUSION MATRIX
   ════════════════════════════════════════════════════════════════════════ */
.cm-grid {{
  display: grid;
  grid-template-columns: auto 1fr 1fr;
  grid-template-rows:  auto 1fr 1fr;
  gap: 8px;
  max-width: 420px;
  margin: 28px 0;
}}
.cm-label {{
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'DM Mono', monospace;
  font-size: 0.65rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
  padding: 8px;
}}
.cm-cell {{
  padding: 20px 16px;
  border-radius: 6px;
  text-align: center;
}}
.cm-cell .cm-count {{
  font-family: 'Playfair Display', serif;
  font-size: 1.6rem;
  font-weight: 700;
  line-height: 1;
  display: block;
}}
.cm-cell .cm-type {{
  font-family: 'DM Mono', monospace;
  font-size: 0.62rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  display: block;
  margin-top: 4px;
}}
.cm-tp {{ background: #dcfce7; color: #15803d; }}
.cm-tn {{ background: #dbeafe; color: #1d4ed8; }}
.cm-fp {{ background: #fef9c3; color: #854d0e; }}
.cm-fn {{ background: #fee2e2; color: #b91c1c; }}

/* ════════════════════════════════════════════════════════════════════════
   SHAP TOP 10
   ════════════════════════════════════════════════════════════════════════ */
.shap-bar-list {{
  margin: 24px 0;
}}
.shap-row {{
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}}
.shap-rank {{
  font-family: 'DM Mono', monospace;
  font-size: 0.65rem;
  color: var(--muted);
  width: 20px;
  text-align: right;
  flex-shrink: 0;
}}
.shap-name {{
  font-family: 'DM Mono', monospace;
  font-size: 0.78rem;
  color: var(--ink-soft);
  width: 200px;
  flex-shrink: 0;
}}
.shap-bar-outer {{
  flex: 1;
  background: var(--border);
  border-radius: 2px;
  height: 8px;
  overflow: hidden;
}}
.shap-bar-inner {{
  height: 100%;
  background: var(--amber);
  border-radius: 2px;
}}
.shap-val {{
  font-family: 'DM Mono', monospace;
  font-size: 0.72rem;
  color: var(--slate);
  width: 52px;
  text-align: right;
  flex-shrink: 0;
}}

/* ════════════════════════════════════════════════════════════════════════
   FOOTER
   ════════════════════════════════════════════════════════════════════════ */
.report-footer {{
  background: var(--ink);
  color: #64748b;
  padding: 40px 72px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 80px;
}}
.footer-left {{
  font-family: 'Playfair Display', serif;
  font-size: 1rem;
  color: #94a3b8;
}}
.footer-right {{
  font-family: 'DM Mono', monospace;
  font-size: 0.68rem;
  letter-spacing: 0.1em;
  line-height: 2;
  text-align: right;
}}

/* ════════════════════════════════════════════════════════════════════════
   MISC
   ════════════════════════════════════════════════════════════════════════ */
p {{ margin-bottom: 1em; }}
p:last-child {{ margin-bottom: 0; }}
strong {{ font-weight: 500; color: var(--ink); }}
code {{
  font-family: 'DM Mono', monospace;
  font-size: 0.82em;
  background: var(--surface);
  border: 1px solid var(--border);
  padding: 1px 5px;
  border-radius: 3px;
  color: var(--ink-soft);
}}

.two-col {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 32px;
  margin: 28px 0;
}}

h3 {{
  font-family: 'Playfair Display', serif;
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--ink);
  margin: 28px 0 12px;
}}
h4 {{
  font-family: 'DM Mono', monospace;
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--amber);
  margin: 24px 0 8px;
}}

ul {{
  padding-left: 1.4em;
  margin-bottom: 1em;
}}
ul li {{
  font-size: 0.9rem;
  color: var(--slate);
  margin-bottom: 5px;
  line-height: 1.6;
}}
ul li strong {{ color: var(--ink); }}

</style>
</head>
<body>

<!-- ══════════════════════════════════════════════════════════════════════
     COVER PAGE
     ══════════════════════════════════════════════════════════════════════ -->
<div class="cover">
  <div>
    <div class="cover-eyebrow">End-to-End Machine Learning Portfolio · CRISP-DM</div>
    <div class="cover-title">
      Predicting Loan<br><em>Default Risk</em><br>at Origination
    </div>
    <div class="cover-divider"></div>
    <div class="cover-subtitle">
      A complete 8-stage machine learning pipeline applied to 2.26 million
      LendingClub loan records — from raw SQL to a tuned XGBoost classifier
      with full SHAP explainability and business impact quantification.
    </div>
  </div>

  <div>
    <div class="cover-metrics">
      <div class="cover-metric">
        <div class="cover-metric-value">{rec:.0%}</div>
        <div class="cover-metric-label">Default Recall</div>
      </div>
      <div class="cover-metric">
        <div class="cover-metric-value">{roc:.4f}</div>
        <div class="cover-metric-label">ROC-AUC</div>
      </div>
      <div class="cover-metric">
        <div class="cover-metric-value">+$628M</div>
        <div class="cover-metric-label">Net Value (Test Set)</div>
      </div>
      <div class="cover-metric">
        <div class="cover-metric-value">2.26M</div>
        <div class="cover-metric-label">Loan Records</div>
      </div>
    </div>

    <div class="cover-footer">
      <div class="cover-meta">
        Dataset · LendingClub 2007–2016<br>
        Model · XGBoost · Optuna-tuned · 1,046 estimators<br>
        Methodology · CRISP-DM · 8 stages<br>
        Generated · {datetime.now().strftime("%B %d, %Y")}
      </div>
      <div class="cover-badge">Portfolio Report</div>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════════════════════════════
     SECTION 1 — EXECUTIVE SUMMARY
     ══════════════════════════════════════════════════════════════════════ -->
<div class="container">

<div class="section page-break">
  <div class="section-num">01 · Executive Summary</div>
  <div class="section-title">The Bottom Line</div>
  <div class="section-lead">
    A tuned XGBoost classifier identifies 87.4% of loans that will default —
    generating an estimated <strong>+$628 million</strong> in net value on the
    held-out test set of 264,370 loans versus a no-model baseline.
  </div>

  <div class="metric-grid metric-grid-5">
    <div class="metric-card status-fail">
      <div class="metric-label">ROC-AUC</div>
      <div class="metric-value">{roc:.4f}</div>
      <div class="metric-target">Target ≥ 0.80</div>
      <span class="metric-badge badge-fail">Below minimum</span>
    </div>
    <div class="metric-card status-fail">
      <div class="metric-label">PR-AUC</div>
      <div class="metric-value">{prauc:.4f}</div>
      <div class="metric-target">Target ≥ 0.70</div>
      <span class="metric-badge badge-fail">Below minimum</span>
    </div>
    <div class="metric-card status-pass">
      <div class="metric-label">Recall</div>
      <div class="metric-value">{rec:.4f}</div>
      <div class="metric-target">Stretch ≥ 0.80</div>
      <span class="metric-badge badge-pass">Exceeds stretch</span>
    </div>
    <div class="metric-card">
      <div class="metric-label">Precision</div>
      <div class="metric-value">{prec:.4f}</div>
      <div class="metric-target">—</div>
      <span class="metric-badge badge-note">Threshold {thr:.4f}</span>
    </div>
    <div class="metric-card">
      <div class="metric-label">F1 Score</div>
      <div class="metric-value">{f1:.4f}</div>
      <div class="metric-target">—</div>
      <span class="metric-badge badge-note">Weighted optimum</span>
    </div>
  </div>

  <div class="callout-dark">
    <div class="callout-title">Honest Assessment — Information Ceiling</div>
    <p>
      ROC-AUC and PR-AUC fell short of minimum targets — and this is a
      <strong>diagnostic finding, not a modelling failure</strong>. The dominant
      predictor, <code>int_rate</code>, is LendingClub's own compressed risk
      assessment. The model largely learns to agree with the lender's pricing
      judgment; it cannot systematically discover defaults that the lender's own
      pricing model missed using only the same application-time information.
      50 Bayesian optimisation trials (Optuna) produced only +0.0018 ROC-AUC
      improvement — confirming the bottleneck is the feature set, not
      hyperparameter choice.
    </p>
  </div>

  <h3>Benchmark Progression</h3>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Stage</th><th>Configuration</th>
          <th>ROC-AUC</th><th>PR-AUC</th>
          <th>Recall</th><th>Threshold</th>
        </tr>
      </thead>
      <tbody>
        <tr><td>Prior</td><td>Previous attempt (baseline)</td><td>0.700</td><td>~0.500</td><td>0.700</td><td>0.500</td></tr>
        <tr><td>Stage 5 · S1</td><td>XGB — no weighting</td><td>0.7095</td><td>0.3318</td><td>0.0304</td><td>0.500</td></tr>
        <tr><td>Stage 5 · S2</td><td>XGB — class weighted</td><td>0.7099</td><td>0.3317</td><td>0.6602</td><td>0.500</td></tr>
        <tr><td>Stage 5 · S3</td><td>XGB — weighted + opt. threshold</td><td>0.7099</td><td>0.3317</td><td>0.8748</td><td>0.3584</td></tr>
        <tr class="final-row"><td>Stage 6</td><td>XGB — Optuna tuned (final)</td><td>{roc:.4f}</td><td>{prauc:.4f}</td><td>{rec:.4f}</td><td>{thr:.4f}</td></tr>
        <tr class="target-row"><td>—</td><td>Minimum target</td><td>≥ 0.80</td><td>≥ 0.70</td><td>≥ 0.75</td><td>—</td></tr>
      </tbody>
    </table>
  </div>

  <div class="callout">
    <div class="callout-title">Key Takeaway</div>
    <p>95% of the Recall gain came from two non-model changes — class weighting
    and threshold optimisation — not from model complexity. The jump from
    Step 1 (3% Recall) to Step 3 (87.5% Recall) required zero additional
    training, only a change in how the model's scores are used.</p>
  </div>
</div>

<!-- ══════════════════════════════════════════════════════════════════════
     SECTION 2 — BUSINESS PROBLEM
     ══════════════════════════════════════════════════════════════════════ -->
<div class="section page-break">
  <div class="section-num">02 · Business Problem</div>
  <div class="section-title">Asymmetric Cost Framing</div>
  <div class="section-lead">
    Default prediction is not a symmetric classification problem.
    The cost of missing a default is an order of magnitude larger than
    the cost of rejecting a good loan — and every modeling decision flows
    from this asymmetry.
  </div>

  <div class="two-col">
    <div class="impact-card negative">
      <div class="impact-card-label">False Negative — Miss a Default</div>
      <div class="impact-card-value">−$12,000</div>
      <div class="impact-card-desc">
        Bank loses ~80% of the $15,000 principal (Loss Given Default).
        The loan is funded, payments stop, recovery is costly and incomplete.
      </div>
    </div>
    <div class="impact-card positive">
      <div class="impact-card-label">False Positive — Flag a Good Loan</div>
      <div class="impact-card-value">−$1,200</div>
      <div class="impact-card-desc">
        Bank forgoes ~8% annual profit on a loan that would have paid off.
        No capital is lost — only future revenue is foregone.
      </div>
    </div>
  </div>

  <p>The <strong>10:1 cost asymmetry</strong> means the model can tolerate up to 10 false positives
  per true positive and still add net value. The actual ratio in the test set is
  approximately 3.4:1 — well within the profitable zone.</p>

  <h4>Design Implications</h4>
  <ul>
    <li><strong>Optimise for Recall, not Accuracy.</strong> 83% accuracy is trivially achieved by predicting "no default" for everything. Recall measures the fraction of actual defaults caught — the metric that directly translates to avoided losses.</li>
    <li><strong>PR-AUC over ROC-AUC</strong> as the primary ranking metric. With a 17.22% default rate (4.8:1 imbalance), ROC-AUC is overly optimistic about performance in the minority class.</li>
    <li><strong>Threshold optimisation, not default 0.5.</strong> Lowering the decision threshold from 0.50 to 0.3592 raised Recall from 66% to 87.4% with no model retraining required.</li>
    <li><strong>Class weighting before SMOTE.</strong> <code>scale_pos_weight = 4.8</code> (matching the imbalance ratio) achieves equivalent effect to oversampling with zero memory overhead.</li>
  </ul>

  <h3>Target Variable Definition</h3>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Label</th><th>loan_status Values</th></tr></thead>
      <tbody>
        <tr><td><strong>Default = 1</strong></td><td>Charged Off, Default, Late (31–120 days), Does not meet credit policy — Charged Off</td></tr>
        <tr><td><strong>Non-Default = 0</strong></td><td>Fully Paid, Current, In Grace Period, Late (16–30 days), Does not meet credit policy — Fully Paid, Issued</td></tr>
      </tbody>
    </table>
  </div>

  <p>Post-vintage filtering (removing immature 2017–2018 loans with suppressed labels),
  the canonical default rate is <strong>17.22%</strong> — not the raw 12.9% seen in the
  full dataset. All downstream modeling uses this corrected figure.</p>
</div>

<!-- ══════════════════════════════════════════════════════════════════════
     SECTION 3 — PIPELINE
     ══════════════════════════════════════════════════════════════════════ -->
<div class="section page-break">
  <div class="section-num">03 · Pipeline</div>
  <div class="section-title">Eight Stages, One Decision</div>
  <div class="section-lead">
    Each stage produced artifacts consumed by the next — a fully reproducible
    pipeline from raw SQLite to a deployed classifier.
  </div>

  <div class="pipeline">
    <div class="pipeline-stage">
      <div class="pipeline-dot">00</div>
      <div class="pipeline-body">
        <div class="pipeline-stage-title">Business Understanding</div>
        <div class="pipeline-stage-desc">Defined the cost framing (FN:FP ≈ 10:1), target variable, and — critically — a 77-column leakage audit before touching the data. Post-origination fields like <code>recoveries</code>, <code>last_pymnt_amnt</code>, and <code>total_rec_prncp</code> were permanently excluded.</div>
        <span class="pipeline-stage-tag">Artifacts: business_understanding.md · leakage_columns.json</span>
      </div>
    </div>
    <div class="pipeline-stage">
      <div class="pipeline-dot">01</div>
      <div class="pipeline-body">
        <div class="pipeline-stage-title">Exploratory Data Analysis</div>
        <div class="pipeline-stage-desc">Full 2.26M row dataset explored via SQL aggregates (peak memory: ~132 bytes). Grade monotonicity confirmed (A: 3.6% → G: 40.0%). Temporal finding: 2017–2018 vintages have immature labels and must be filtered.</div>
        <span class="pipeline-stage-tag">Strategy: SQL-first · no pandas full load</span>
      </div>
    </div>
    <div class="pipeline-stage">
      <div class="pipeline-dot">02</div>
      <div class="pipeline-body">
        <div class="pipeline-stage-title">Cleaning & Preprocessing</div>
        <div class="pipeline-stage-desc">Vintage filter removed 938,854 rows (41.5%), correcting the default rate from misleading 12.9% to canonical <strong>17.22%</strong>. 90 columns excluded (leakage, identifiers, structural missingness, redundancy). Target encoding for <code>addr_state</code>, sentinel imputation for <code>mths_since_recent_bc</code>.</div>
        <span class="pipeline-stage-tag">Output: 02_cleaned.parquet · 1,321,847 × 81 · 84.6 MB</span>
      </div>
    </div>
    <div class="pipeline-stage">
      <div class="pipeline-dot">03</div>
      <div class="pipeline-body">
        <div class="pipeline-stage-title">Feature Selection</div>
        <div class="pipeline-stage-desc">Four systematic passes: variance threshold (−8), Pearson correlation pruning (−6), Cohen's d review (−0), domain judgment (−0). Notable: <code>sub_grade</code> dropped (r=0.978 with <code>int_rate</code>); <code>fico_range_low</code> dropped (near-identical to high).</div>
        <span class="pipeline-stage-tag">Output: 03_selected_features.json · 79 → 65 features</span>
      </div>
    </div>
    <div class="pipeline-stage">
      <div class="pipeline-dot active">04</div>
      <div class="pipeline-body">
        <div class="pipeline-stage-title">Feature Engineering</div>
        <div class="pipeline-stage-desc">Five engineered features constructed. Top two (<code>fico_int_rate_gap</code> d=0.53, <code>risk_score</code> d=0.51) rank among the strongest predictors in the full feature set. <code>credit_age_months</code> rescued from the dropped date column <code>earliest_cr_line</code>.</div>
        <span class="pipeline-stage-tag">Output: 04_engineered.parquet · 70 features entering modeling</span>
      </div>
    </div>
    <div class="pipeline-stage">
      <div class="pipeline-dot">05</div>
      <div class="pipeline-body">
        <div class="pipeline-stage-title">Baseline Modeling</div>
        <div class="pipeline-stage-desc">Three sequential steps isolated contribution of each intervention. Class weighting (<code>scale_pos_weight=4.8</code>) raised Recall from 3% to 66%. Threshold optimisation then pushed it to 87.5% with no retraining. ROC-AUC was unchanged across all steps.</div>
        <span class="pipeline-stage-tag">XGBoost · scale_pos_weight=4.8 · threshold=0.3584</span>
      </div>
    </div>
    <div class="pipeline-stage">
      <div class="pipeline-dot">06</div>
      <div class="pipeline-body">
        <div class="pipeline-stage-title">Hyperparameter Tuning</div>
        <div class="pipeline-stage-desc">50 Bayesian trials via Optuna across 9 hyperparameters. Best trial #44. ROC-AUC improvement: +0.0018. Near-zero gain confirmed the feature set — not hyperparameters — as the binding constraint.</div>
        <span class="pipeline-stage-tag">Optuna · 50 trials · best PR-AUC val: 0.3349</span>
      </div>
    </div>
    <div class="pipeline-stage">
      <div class="pipeline-dot">07</div>
      <div class="pipeline-body">
        <div class="pipeline-stage-title">Evaluation</div>
        <div class="pipeline-stage-desc">Full held-out test evaluation with SHAP explainability (5,000 stratified samples), calibration analysis, grade-level segmentation, and business impact quantification.</div>
        <span class="pipeline-stage-tag">SHAP · grade segmentation · business impact</span>
      </div>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════════════════════════════
     SECTION 4 — MODEL RESULTS
     ══════════════════════════════════════════════════════════════════════ -->
<div class="section page-break">
  <div class="section-num">04 · Model Results</div>
  <div class="section-title">Performance on 264,370 Held-Out Loans</div>
  <div class="section-lead">
    Confusion matrix, PR/ROC curves, and grade-level segmentation
    on the test set.
  </div>

  <h4>Confusion Matrix (threshold = {thr:.4f})</h4>
  <div class="cm-grid">
    <div class="cm-label"></div>
    <div class="cm-label">Predicted: No Default</div>
    <div class="cm-label">Predicted: Default</div>
    <div class="cm-label">Actual: No Default</div>
    <div class="cm-cell cm-tn">
      <span class="cm-count">{TN:,}</span>
      <span class="cm-type">True Negative</span>
    </div>
    <div class="cm-cell cm-fp">
      <span class="cm-count">{FP:,}</span>
      <span class="cm-type">False Positive</span>
    </div>
    <div class="cm-label">Actual: Default</div>
    <div class="cm-cell cm-fn">
      <span class="cm-count">{FN:,}</span>
      <span class="cm-type">False Negative</span>
    </div>
    <div class="cm-cell cm-tp">
      <span class="cm-count">{TP:,}</span>
      <span class="cm-type">True Positive</span>
    </div>
  </div>

  <p>Of 45,512 actual defaults in the test set, the model catches <strong>{TP:,} ({rec:.1%})</strong>.
  The {FP:,} false positives represent loans that would be incorrectly rejected — at $1,200 each,
  this is the cost of a high-recall strategy. Given the 10:1 FN:FP cost asymmetry, this trade-off
  is strongly net-positive.</p>

  <div class="fig-row">
    <div class="fig">
      <img src="{img_roc}" alt="PR and ROC curves">
      <div class="fig-caption"><strong>Fig 1.</strong> Precision-Recall and ROC curves for the final tuned model. The PR curve shows limited area — inherent to a 17.22% base rate problem.</div>
    </div>
    <div class="fig">
      <img src="{img_cm}" alt="Confusion matrix heatmap">
      <div class="fig-caption"><strong>Fig 2.</strong> Confusion matrix heatmap at the optimised threshold of {thr:.4f}.</div>
    </div>
  </div>

  <h3>Performance by Loan Grade</h3>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Grade</th><th>N (test)</th><th>Default Rate</th>
          <th>Recall</th><th>Precision</th><th>ROC-AUC</th>
        </tr>
      </thead>
      <tbody>
        {grade_rows()}
      </tbody>
    </table>
  </div>
  <p style="font-size:0.82rem;color:var(--muted);margin-top:-12px;">
    Rows shaded amber (D–G) represent high-risk segments where the model is most actionable (Recall ≥ 0.99).
  </p>

  <div class="fig">
    <img src="{img_grade}" alt="Grade-level metrics">
    <div class="fig-caption"><strong>Fig 3.</strong> Recall and Precision by loan grade. Recall rises monotonically A→G; Grade A defaults are largely unpredictable from application-time data.</div>
  </div>

  <div class="fig-row">
    <div class="fig">
      <img src="{img_score_dist}" alt="Score distribution">
      <div class="fig-caption"><strong>Fig 4.</strong> Predicted probability distributions for default vs non-default loans. Mean delta of 0.137 illustrates the heavy overlap causing the ROC-AUC ceiling.</div>
    </div>
    <div class="fig">
      <img src="{img_calibration}" alt="Calibration curve">
      <div class="fig-caption"><strong>Fig 5.</strong> Calibration curve. Scores should be interpreted as relative risk rankings, not literal probability estimates. Post-hoc calibration (Platt scaling) is recommended for production use.</div>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════════════════════════════
     SECTION 5 — EXPLAINABILITY
     ══════════════════════════════════════════════════════════════════════ -->
<div class="section page-break">
  <div class="section-num">05 · Explainability</div>
  <div class="section-title">What Drives Default Risk?</div>
  <div class="section-lead">
    SHAP (SHapley Additive exPlanations) values decompose each prediction into
    per-feature contributions — grounded in cooperative game theory, not heuristics.
    Computed on a stratified 5,000-loan sample of the test set.
  </div>

  <h4>Top 10 Features — Mean |SHAP| Value</h4>
  <div class="shap-bar-list">
    <div class="shap-row"><span class="shap-rank">1</span><span class="shap-name">int_rate</span><div class="shap-bar-outer"><div class="shap-bar-inner" style="width:100%"></div></div><span class="shap-val">0.27618</span></div>
    <div class="shap-row"><span class="shap-rank">2</span><span class="shap-name">acc_open_past_24mths</span><div class="shap-bar-outer"><div class="shap-bar-inner" style="width:52.5%"></div></div><span class="shap-val">0.14511</span></div>
    <div class="shap-row"><span class="shap-rank">3</span><span class="shap-name">term</span><div class="shap-bar-outer"><div class="shap-bar-inner" style="width:41.8%"></div></div><span class="shap-val">0.11536</span></div>
    <div class="shap-row"><span class="shap-rank">4</span><span class="shap-name">fico_range_high</span><div class="shap-bar-outer"><div class="shap-bar-inner" style="width:36.9%"></div></div><span class="shap-val">0.10202</span></div>
    <div class="shap-row"><span class="shap-rank">5</span><span class="shap-name">risk_score ✦</span><div class="shap-bar-outer"><div class="shap-bar-inner" style="width:33.2%"></div></div><span class="shap-val">0.09181</span></div>
    <div class="shap-row"><span class="shap-rank">6</span><span class="shap-name">loan_to_income ✦</span><div class="shap-bar-outer"><div class="shap-bar-inner" style="width:29.2%"></div></div><span class="shap-val">0.08061</span></div>
    <div class="shap-row"><span class="shap-rank">7</span><span class="shap-name">total_bc_limit</span><div class="shap-bar-outer"><div class="shap-bar-inner" style="width:22.7%"></div></div><span class="shap-val">0.06284</span></div>
    <div class="shap-row"><span class="shap-rank">8</span><span class="shap-name">home_ownership_RENT</span><div class="shap-bar-outer"><div class="shap-bar-inner" style="width:21.0%"></div></div><span class="shap-val">0.05800</span></div>
    <div class="shap-row"><span class="shap-rank">9</span><span class="shap-name">mo_sin_old_rev_tl_op</span><div class="shap-bar-outer"><div class="shap-bar-inner" style="width:20.3%"></div></div><span class="shap-val">0.05608</span></div>
    <div class="shap-row"><span class="shap-rank">10</span><span class="shap-name">inq_last_6mths</span><div class="shap-bar-outer"><div class="shap-bar-inner" style="width:19.2%"></div></div><span class="shap-val">0.05305</span></div>
  </div>
  <p style="font-size:0.78rem;color:var(--muted);margin-top:-4px;">✦ Engineered features from Stage 4</p>

  <div class="callout">
    <div class="callout-title">Key Insight — int_rate Dominance</div>
    <p><code>int_rate</code> is 1.9× more impactful than the #2 feature and ~4× in XGBoost gain
    importance. This reflects a fundamental truth: LendingClub's own pricing model compresses
    the borrower's risk profile into a single number — and our model largely learns to re-rank
    that existing assessment. Both engineered features (<code>risk_score</code> #5,
    <code>loan_to_income</code> #6) outperform many raw features, validating Stage 4's
    engineering pass.</p>
  </div>

  <div class="fig-row">
    <div class="fig">
      <img src="{img_shap_bar}" alt="SHAP global bar chart">
      <div class="fig-caption"><strong>Fig 6.</strong> Global SHAP feature importance — mean absolute SHAP value across all 5,000 samples.</div>
    </div>
    <div class="fig">
      <img src="{img_shap_beeswarm}" alt="SHAP beeswarm plot">
      <div class="fig-caption"><strong>Fig 7.</strong> SHAP beeswarm. Each dot = one loan. Position = contribution. Color = feature value (red = high, blue = low). Confirms directional monotonicity of top predictors.</div>
    </div>
  </div>

  <h3>Individual Prediction Explanations</h3>

  <h4>Case 1 — True Positive (prob = 0.930) · Classic High-Risk Profile</h4>
  <div class="fig">
    <img src="{img_waterfall_tp}" alt="SHAP waterfall — true positive">
    <div class="fig-caption"><strong>Fig 8.</strong> Waterfall plot for a correctly-caught default. Profile: <code>int_rate</code>=26.57%, 60-month term, <code>risk_score</code>=0.87, <code>loan_to_income</code>=0.44, FICO=704. Every feature pushes in the same direction — the model's 93% confidence is well-founded.</div>
  </div>

  <h4>Case 2 — False Negative (prob = 0.358 vs threshold 0.359) · The Hard Case</h4>
  <div class="fig">
    <img src="{img_waterfall_fn}" alt="SHAP waterfall — false negative">
    <div class="fig-caption"><strong>Fig 9.</strong> Waterfall plot for a missed default. Profile: <code>int_rate</code>=9.17%, 36-month term, <code>risk_score</code>=0.33, low debt burden, 12-year credit history. This borrower looked creditworthy at origination — the eventual default was almost certainly caused by a post-origination event (job loss, medical emergency) invisible in any application snapshot. This is the irreducible uncertainty of origination-time prediction.</div>
  </div>
</div>

<!-- ══════════════════════════════════════════════════════════════════════
     SECTION 6 — BUSINESS IMPACT
     ══════════════════════════════════════════════════════════════════════ -->
<div class="section page-break">
  <div class="section-num">06 · Business Impact</div>
  <div class="section-title">Quantifying the Value</div>
  <div class="section-lead">
    Translating model performance into financial outcomes using
    standard consumer lending assumptions.
  </div>

  <div class="impact-grid">
    <div class="impact-card positive">
      <div class="impact-card-label">Losses Avoided (TP × $12,000)</div>
      <div class="impact-card-value">+${losses_avoided:,.0f}</div>
      <div class="impact-card-desc">{TP:,} defaults correctly flagged</div>
    </div>
    <div class="impact-card positive">
      <div class="impact-card-label">Profit Earned (TN × $1,200)</div>
      <div class="impact-card-value">+${profit_earned:,.0f}</div>
      <div class="impact-card-desc">{TN:,} good loans correctly approved</div>
    </div>
    <div class="impact-card negative">
      <div class="impact-card-label">Losses Incurred (FN × $12,000)</div>
      <div class="impact-card-value">−${losses_incurred:,.0f}</div>
      <div class="impact-card-desc">{FN:,} defaults missed by the model</div>
    </div>
    <div class="impact-card negative">
      <div class="impact-card-label">Profit Foregone (FP × $1,200)</div>
      <div class="impact-card-value">−${profit_foregone:,.0f}</div>
      <div class="impact-card-desc">{FP:,} good loans incorrectly rejected</div>
    </div>
  </div>

  <div class="impact-total">
    <div>
      <div class="impact-total-label">Net Model Advantage (test set)</div>
      <div class="impact-total-value">+${net_advantage:,.0f}</div>
      <div class="impact-total-sub">vs. no-model baseline (approve everything)</div>
    </div>
    <div style="text-align:right;">
      <div style="font-family:'DM Mono',monospace;font-size:0.7rem;color:#64748b;line-height:2.2;">
        Avg loan: $15,000<br>
        LGD: 80% → $12,000/default<br>
        Margin: 8% → $1,200/approval<br>
        Break-even FP:TP ratio: 10:1<br>
        Actual FP:TP ratio: 3.4:1 ✅
      </div>
    </div>
  </div>

  <div class="callout">
    <div class="callout-title">Sensitivity Note</div>
    <p>These figures are sensitive to LGD (50–90% range in practice) and platform margin (5–12%).
    The directional conclusion — large net positive value — is robust across all reasonable
    combinations. The critical invariant is that FN cost &gt; FP cost by a factor greater
    than 1, which holds across the consumer lending industry.</p>
  </div>
</div>

<!-- ══════════════════════════════════════════════════════════════════════
     SECTION 7 — LIMITATIONS
     ══════════════════════════════════════════════════════════════════════ -->
<div class="section page-break">
  <div class="section-num">07 · Limitations</div>
  <div class="section-title">What This Model Cannot Do</div>
  <div class="section-lead">
    Intellectual honesty is a professional skill. Here is an unvarnished
    accounting of this model's constraints.
  </div>

  <div class="limitation">
    <div class="limitation-num">01</div>
    <div>
      <div class="limitation-title">ROC-AUC and PR-AUC Below Target</div>
      <div class="limitation-body">ROC-AUC = 0.7117 (target ≥ 0.80). The score distribution analysis shows a mean separation of only 0.137 between default and non-default predicted probabilities — heavy distributional overlap that reflects the fundamental limits of application-time data. Beating 0.80 would likely require external bureau data or bank transaction history not present in the LendingClub dataset.</div>
    </div>
  </div>

  <div class="limitation">
    <div class="limitation-num">02</div>
    <div>
      <div class="limitation-title">Calibration — Scores Are Not Probabilities</div>
      <div class="limitation-body">XGBoost trained with class weighting produces shifted probability estimates. A loan scoring 0.60 does not have a 60% true default probability. Scores should be used as relative risk rankings only. Platt scaling or isotonic regression post-processing would be required before using outputs for risk pricing or regulatory capital calculations.</div>
    </div>
  </div>

  <div class="limitation">
    <div class="limitation-num">03</div>
    <div>
      <div class="limitation-title">Grade A Recall = 15.2%</div>
      <div class="limitation-body">The model misses 85% of Grade A defaults. These borrowers have low rates, strong FICO scores, and clean credit histories at origination — making them statistically indistinguishable from non-defaulters. Grade A defaults are overwhelmingly caused by post-origination shocks (job loss, medical emergency) that no application-time model can predict.</div>
    </div>
  </div>

  <div class="limitation">
    <div class="limitation-num">04</div>
    <div>
      <div class="limitation-title">Vintage Scope — 2007–2016 Only</div>
      <div class="limitation-body">Training distribution excludes recent macroeconomic regimes: COVID-era payment behaviour, 2022–2023 rate environment, post-pandemic employment patterns. Model performance on loans originated after 2016 is unknown and likely degraded under materially different economic conditions.</div>
    </div>
  </div>

  <div class="limitation">
    <div class="limitation-num">05</div>
    <div>
      <div class="limitation-title">Business Impact Assumptions</div>
      <div class="limitation-body">The +$628M estimate assumes LGD = 80% and margin = 8% — reasonable industry estimates but not verified against actual LendingClub financials. Real deployment also involves regulatory constraints (ECOA fair lending), model risk management requirements, and application volume effects not captured in this analysis.</div>
    </div>
  </div>
</div>

<!-- ══════════════════════════════════════════════════════════════════════
     SECTION 8 — FUTURE WORK
     ══════════════════════════════════════════════════════════════════════ -->
<div class="section">
  <div class="section-num">08 · Future Work</div>
  <div class="section-title">Highest-Leverage Next Steps</div>

  <div class="table-wrap">
    <table>
      <thead>
        <tr><th>#</th><th>Improvement</th><th>Effort</th><th>Expected Impact</th></tr>
      </thead>
      <tbody>
        <tr><td>1</td><td><strong>Calibration post-processing</strong> — Platt scaling or isotonic regression via <code>CalibratedClassifierCV</code></td><td>Low</td><td>Enables probability interpretation; required for regulatory use</td></tr>
        <tr><td>2</td><td><strong>Separate Grade A model</strong> — features focused on employment stability and macro exposure, not credit utilisation</td><td>Medium</td><td>Targeted improvement for the most unpredictable segment</td></tr>
        <tr><td>3</td><td><strong>Monotonic constraints</strong> on <code>int_rate</code> (↑ rate → ↑ default) and <code>fico_range_high</code> (↑ FICO → ↓ default) in XGBoost</td><td>Low</td><td>Prevents overfitting artifacts; improves stakeholder trust and interpretability</td></tr>
        <tr><td>4</td><td><strong>LightGBM comparison</strong> — typically 3–10× faster training, often comparable performance on tabular data</td><td>Medium</td><td>Production retraining latency; marginal performance gain likely</td></tr>
        <tr><td>5</td><td><strong>Segment-specific thresholds</strong> — grade-level optimal cutoffs rather than a single global threshold</td><td>Low</td><td>Improved Precision/Recall trade-off at each grade without model retraining</td></tr>
        <tr><td>6</td><td><strong>Behavioural features</strong> — payment history, utilisation trajectory from monthly servicer snapshots</td><td>High</td><td>Breaks the information ceiling; fundamentally different problem (early-warning, not origination)</td></tr>
      </tbody>
    </table>
  </div>
</div>

</div><!-- /container -->

<!-- ══════════════════════════════════════════════════════════════════════
     FOOTER
     ══════════════════════════════════════════════════════════════════════ -->
<div class="report-footer">
  <div class="footer-left">LendingClub Default Prediction</div>
  <div class="footer-right">
    CRISP-DM · 8 Stages · XGBoost + Optuna<br>
    Dataset: 2.26M rows · 151 columns · 2007–2016<br>
    Generated: {datetime.now().strftime("%B %d, %Y")}
  </div>
</div>

</body>
</html>"""

# ── Write output ───────────────────────────────────────────────────────────────
out_dir = Path("reports")
out_dir.mkdir(exist_ok=True)
out_path = out_dir / "lending_club_report.html"
out_path.write_text(HTML, encoding="utf-8")

size_kb = out_path.stat().st_size / 1024
print(f"✅  Report generated: {out_path}")
print(f"    Size: {size_kb:.0f} KB")
print()
print("Next steps:")
print("  1. Open reports/lending_club_report.html in Chrome")
print("  2. File → Print (or Cmd+P)")
print("  3. Destination: Save as PDF")
print("  4. More settings: Paper = A4, Margins = None, ✅ Background graphics")
