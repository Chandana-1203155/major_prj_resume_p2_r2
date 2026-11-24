"""Global CSS for the app (light, professional theme)."""

import streamlit as st


_STYLES = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* =====================================================================
   Design tokens
   ===================================================================== */
:root {
    --bg: #f4f6fb;
    --surface: #ffffff;
    --surface-alt: #f8fafc;
    --border: #e2e8f0;
    --border-strong: #cbd5e1;
    --text: #0f172a;
    --text-2: #334155;
    --muted: #64748b;
    --accent: #2563eb;
    --accent-dark: #1d4ed8;
    --accent-soft: #eff4ff;
    --success: #16a34a;
    --warning: #d97706;
    --danger: #dc2626;
    --radius: 12px;
    --radius-sm: 8px;
    --shadow: 0 1px 2px rgba(15, 23, 42, .05), 0 1px 3px rgba(15, 23, 42, .04);
    --shadow-md: 0 4px 14px rgba(15, 23, 42, .08);
    --font: 'Inter', 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, 'Helvetica Neue', Arial, sans-serif;
}

/* =====================================================================
   Base
   ===================================================================== */
html, body, .stApp, [data-testid="stAppViewContainer"] {
    background-color: var(--bg);
    font-family: var(--font);
    color: var(--text);
}
.stApp { color-scheme: light; }

/* Streamlit chrome */
#MainMenu, footer { visibility: hidden; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stDecoration"] { display: none; }

/* Page width + rhythm */
[data-testid="stMainBlockContainer"], .block-container {
    max-width: 1280px;
    padding: 2rem 2.5rem 4rem 2.5rem;
}
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] { gap: 1rem; }

/* Typography */
h1, h2, h3, h4, h5, h6 {
    font-family: var(--font) !important;
    color: var(--text);
    letter-spacing: -0.01em;
}
.stApp h1 { font-size: 1.9rem; font-weight: 800; }
.stApp h2 {
    font-size: 1.6rem; font-weight: 700;
    padding-bottom: .6rem; margin-bottom: .25rem;
    border-bottom: 1px solid var(--border);
}
.stApp h3 { font-size: 1.15rem; font-weight: 700; }
.stApp h4 { font-size: 1rem; font-weight: 700; }
.stApp p, .stApp li, .stApp label { font-family: var(--font); }
.stApp p, .stApp li { line-height: 1.6; }
[data-testid="stCaptionContainer"], .stApp small { color: var(--muted); }
.stApp hr { border: none; border-top: 1px solid var(--border); margin: 1.25rem 0; }
.stApp a { color: var(--accent); }

/* =====================================================================
   Sidebar
   ===================================================================== */
section[data-testid="stSidebar"] {
    background-color: var(--surface);
    border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] > div { padding-top: .5rem; }
section[data-testid="stSidebar"] hr { margin: 1rem 0; }

.brand { display: flex; align-items: center; gap: .75rem; padding: .25rem 0 .25rem 0; }
.brand-mark {
    width: 40px; height: 40px; border-radius: 10px; flex-shrink: 0;
    background: linear-gradient(135deg, #2563eb, #1d4ed8);
    color: #fff; font-weight: 800; font-size: 1.05rem; letter-spacing: .01em;
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 2px 6px rgba(37, 99, 235, .35);
}
.brand-name { font-size: 1.15rem; font-weight: 800; color: var(--text); line-height: 1.15; }
.brand-tag { font-size: .75rem; color: var(--muted); margin-top: .1rem; }

.side-label { font-size: .75rem; font-weight: 600; color: var(--muted); margin: 0 0 .5rem .25rem; }

/* Navigation (radio rendered as a vertical menu) */
section[data-testid="stSidebar"] [data-testid="stRadio"] > label { display: none; }
section[data-testid="stSidebar"] [role="radiogroup"] { gap: .2rem; }
section[data-testid="stSidebar"] [role="radiogroup"] label {
    width: 100%;
    padding: .55rem .8rem;
    border-radius: var(--radius-sm);
    border: 1px solid transparent;
    cursor: pointer;
    transition: background .12s ease, border-color .12s ease;
}
section[data-testid="stSidebar"] [role="radiogroup"] label:hover { background: var(--surface-alt); }
section[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child:not(:has([data-testid="stMarkdownContainer"])) { display: none; }
section[data-testid="stSidebar"] [role="radiogroup"] label p { font-size: .92rem; font-weight: 500; color: var(--text-2); margin: 0; }
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
    background: var(--accent-soft);
    border-color: #c7d7fb;
}
section[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p { color: var(--accent-dark); font-weight: 700; }

/* Sidebar summary */
.side-stats { display: flex; flex-direction: column; gap: .5rem; }
.side-stat {
    display: flex; align-items: center; justify-content: space-between;
    background: var(--surface-alt); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: .55rem .8rem;
}
.side-stat .s-name { font-size: .82rem; color: var(--text-2); }
.side-stat .s-num { font-size: 1.05rem; font-weight: 800; }

/* =====================================================================
   Buttons  (consistent size, clear hierarchy, never stretched oddly)
   ===================================================================== */
.stButton > button,
.stDownloadButton > button,
[data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-primary"],
[data-testid="stFormSubmitButton"] > button {
    font-family: var(--font);
    font-size: .9rem;
    font-weight: 600;
    min-height: 2.6rem;
    padding: .45rem 1.1rem;
    border-radius: var(--radius-sm);
    border: 1px solid var(--border-strong);
    background: var(--surface);
    color: var(--text);
    box-shadow: var(--shadow);
    transition: background .12s ease, border-color .12s ease, box-shadow .12s ease;
    white-space: normal;
    line-height: 1.25;
}
.stButton > button:hover,
.stDownloadButton > button:hover {
    border-color: var(--accent);
    color: var(--accent-dark);
    background: var(--accent-soft);
}
.stButton > button:focus-visible,
.stDownloadButton > button:focus-visible {
    outline: 3px solid rgba(37, 99, 235, .35);
    outline-offset: 1px;
}
/* Primary */
.stButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"],
[data-testid="stBaseButton-primary"] {
    background: var(--accent);
    border-color: var(--accent);
    color: #ffffff;
}
.stButton > button[kind="primary"] p,
[data-testid="stBaseButton-primary"] p { color: #ffffff; }
.stButton > button[kind="primary"]:hover,
[data-testid="stBaseButton-primary"]:hover {
    background: var(--accent-dark);
    border-color: var(--accent-dark);
    color: #ffffff;
}
/* Disabled */
.stButton > button:disabled,
.stDownloadButton > button:disabled {
    background: #f1f5f9;
    border-color: var(--border);
    color: #94a3b8;
    box-shadow: none;
    cursor: not-allowed;
}
.stButton > button:disabled p { color: #94a3b8; }

/* Inside columns every button fills its column, so rows line up evenly */
[data-testid="stColumn"] .stButton > button,
[data-testid="stColumn"] .stDownloadButton > button,
[data-testid="stColumn"] [data-testid="stButton"] > button { width: 100%; }

/* The main call-to-action */
.st-key-analyze_candidates button,
.st-key-generate_comparison button {
    width: 100%;
    min-height: 3rem;
    font-size: 1rem;
    font-weight: 700;
}
.st-key-analyze_candidates button { background: var(--accent); border-color: var(--accent); color: #fff; }
.st-key-analyze_candidates button p { color: #fff; }
.st-key-analyze_candidates button:hover { background: var(--accent-dark); border-color: var(--accent-dark); color: #fff; }
.st-key-analyze_candidates button:disabled { background: #e2e8f0; border-color: #e2e8f0; color: #94a3b8; }
.st-key-analyze_candidates button:disabled p { color: #94a3b8; }

/* Destructive actions */
.st-key-reset_data button, [class*="st-key-remove_candidate_"] button {
    background: #fff; border-color: #fca5a5; color: var(--danger);
}
.st-key-reset_data button p, [class*="st-key-remove_candidate_"] button p { color: var(--danger); }
.st-key-reset_data button:hover, [class*="st-key-remove_candidate_"] button:hover {
    background: var(--danger); border-color: var(--danger); color: #fff;
}
.st-key-reset_data button:hover p, [class*="st-key-remove_candidate_"] button:hover p { color: #fff; }
[class*="st-key-remove_resume_"] button { min-height: 2.2rem; padding: .25rem .75rem; font-size: .82rem; }

/* =====================================================================
   Form controls
   ===================================================================== */
[data-testid="stWidgetLabel"] p, .stApp label p {
    font-size: .85rem; font-weight: 600; color: var(--text-2);
}
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {
    background: var(--surface);
    border-radius: var(--radius-sm);
}
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {
    border: 1px solid var(--border-strong);
}
[data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within, [data-baseweb="select"] > div:focus-within {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(37, 99, 235, .15);
}
[data-testid="stNumberInput"] button { border-radius: 6px; }

/* File uploader */
[data-testid="stFileUploaderDropzone"] {
    background: var(--surface-alt);
    border: 1.5px dashed var(--border-strong);
    border-radius: var(--radius);
    padding: 1.1rem 1.25rem;
}
[data-testid="stFileUploaderDropzone"]:hover { border-color: var(--accent); background: var(--accent-soft); }
[data-testid="stFileUploaderDropzone"] button { min-height: 2.3rem; width: auto; }

/* Alerts */
[data-testid="stAlert"] { border-radius: var(--radius-sm); border: 1px solid var(--border); }

/* Progress */
[data-testid="stProgress"] > div > div { border-radius: 999px; }

/* Tabs */
[data-baseweb="tab-list"] { gap: .25rem; border-bottom: 1px solid var(--border); }
button[data-baseweb="tab"] { font-family: var(--font); font-weight: 600; padding: .6rem 1rem; color: var(--muted); }
button[data-baseweb="tab"][aria-selected="true"] { color: var(--accent-dark); }
[data-baseweb="tab-highlight"] { background-color: var(--accent); height: 3px; }
[data-baseweb="tab-border"] { display: none; }

/* Expanders */
[data-testid="stExpander"] {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    overflow: hidden;
}
[data-testid="stExpander"] details { border: none; }
[data-testid="stExpander"] summary { padding: .8rem 1rem; font-weight: 600; }
[data-testid="stExpander"] summary:hover { background: var(--surface-alt); }
[data-testid="stExpander"] [data-testid="stExpander"] { box-shadow: none; background: var(--surface-alt); }

/* Bordered containers act as cards */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--surface);
    border-color: var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
}
div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--surface-alt);
    box-shadow: none;
}

/* Tables / dataframes */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    box-shadow: var(--shadow);
}

/* Sliders */
[data-testid="stSlider"] { padding-bottom: .25rem; }

/* =====================================================================
   Evaluation page: step cards
   ===================================================================== */
.section-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.25rem; margin-bottom: 1rem; box-shadow: var(--shadow); }
.section-header {
    display: flex; align-items: center; gap: .7rem;
    margin-bottom: .25rem; font-size: 1.1rem; font-weight: 700; color: var(--text);
}
.section-header .step-icon {
    display: inline-flex; align-items: center; justify-content: center;
    width: 36px; height: 36px; border-radius: 10px;
    background: var(--accent-soft); font-size: 1.15rem;
}
.section-note {
    color: var(--muted); font-size: .9rem; margin: .25rem 0 .5rem 0;
    padding: .65rem .9rem; background: var(--accent-soft);
    border: 1px solid #dbe6fd; border-radius: var(--radius-sm);
}
.empty-state-card {
    background: var(--surface-alt); border: 1.5px dashed var(--border-strong);
    border-radius: var(--radius); padding: 1.75rem; text-align: center; color: var(--muted);
}
.result-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.25rem; margin-bottom: 1rem; }

/* =====================================================================
   Dashboard components
   ===================================================================== */
.dash-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
.dash-kpi {
    background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius);
    padding: 1rem 1.1rem; text-align: left; box-shadow: var(--shadow);
    border-top: 3px solid var(--accent);
}
.dash-kpi .label { color: var(--muted); font-size: .8rem; font-weight: 600; }
.dash-kpi .val { font-size: 1.85rem; font-weight: 800; margin-top: .2rem; line-height: 1.15; }

.kpi-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 1rem 1.1rem; box-shadow: var(--shadow); }
.kpi-title { color: var(--muted); font-size: .8rem; font-weight: 600; }
.kpi-value { font-size: 1.8rem; font-weight: 800; }

.chart-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.25rem 1.5rem; margin-bottom: 1.5rem; box-shadow: var(--shadow); }
.chart-title { color: var(--text); font-size: 1rem; font-weight: 700; margin-bottom: 1rem; }

/* CSS bar chart */
.css-bar-chart { display: flex; flex-direction: column; gap: .55rem; }
.bar-row { display: flex; align-items: center; gap: .7rem; }
.bar-label { color: var(--text-2); font-size: .82rem; min-width: 120px; text-align: right; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bar-track { flex: 1; height: 24px; background: #eef2f7; border-radius: 6px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 6px; display: flex; align-items: center; justify-content: flex-end; padding-right: 8px; font-size: .72rem; font-weight: 700; color: #fff; transition: width .4s ease; min-width: 24px; }

/* CSS donut */
.donut-wrap { display: flex; justify-content: center; align-items: center; gap: 1.75rem; flex-wrap: wrap; }
.donut { width: 160px; height: 160px; border-radius: 50%; position: relative; display: flex; align-items: center; justify-content: center; }
.donut-hole { width: 98px; height: 98px; border-radius: 50%; background: var(--surface); display: flex; align-items: center; justify-content: center; flex-direction: column; }
.donut-hole .num { color: var(--text); font-size: 1.35rem; font-weight: 800; line-height: 1.1; }
.donut-hole .sub { color: var(--muted); font-size: .68rem; }
.donut-legend { display: flex; flex-direction: column; gap: .45rem; }
.legend-item { display: flex; align-items: center; gap: .5rem; font-size: .82rem; color: var(--text-2); }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }

/* Ranking table */
.rank-table { width: 100%; border-collapse: separate; border-spacing: 0; }
.rank-table th { background: #f1f5f9; color: var(--text-2); padding: .65rem .85rem; font-size: .78rem; font-weight: 700; text-align: left; border-bottom: 1px solid var(--border); }
.rank-table th:first-child { border-radius: 8px 0 0 0; }
.rank-table th:last-child { border-radius: 0 8px 0 0; }
.rank-table td { padding: .65rem .85rem; color: var(--text); border-bottom: 1px solid #eef2f7; font-size: .86rem; vertical-align: top; }
.rank-table tr:hover td { background: var(--surface-alt); }
.rank-table .score-pill { display: inline-block; padding: 2px 10px; border-radius: 20px; font-weight: 700; font-size: .78rem; }

/* Badge */
.badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: .74rem; font-weight: 600; margin: 1px 2px 1px 0; }
.badge-green { background: rgba(22,163,74,.12); color: #15803d; }
.badge-yellow { background: rgba(217,119,6,.12); color: #b45309; }
.badge-red { background: rgba(220,38,38,.10); color: #b91c1c; }
.badge-blue { background: rgba(37,99,235,.10); color: #1d4ed8; }

/* Layout helpers */
.dash-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem; }
.dash-row > .chart-card { margin-bottom: 0; min-width: 0; overflow-x: auto; }
@media (max-width: 900px) { .dash-row { grid-template-columns: 1fr; } }

.stat-row { display: flex; gap: .85rem; flex-wrap: wrap; margin-bottom: 1rem; }
.stat-mini { flex: 1; min-width: 130px; background: var(--surface-alt); border: 1px solid var(--border); border-radius: 10px; padding: .85rem; text-align: center; }
.stat-mini .s-val { font-size: 1.15rem; font-weight: 700; }
.stat-mini .s-lbl { font-size: .74rem; color: var(--muted); margin-top: .15rem; }

/* Narrow screens */
@media (max-width: 768px) {
    [data-testid="stMainBlockContainer"], .block-container { padding: 1.25rem 1rem 3rem 1rem; }
}
</style>
"""


def inject_styles():
    st.markdown(_STYLES, unsafe_allow_html=True)
