"""Reusable GALEX-inspired visual tokens and Streamlit presentation helpers."""
import html

COLORS = {
    "navy": "#152E4D",
    "navy_2": "#21486F",
    "steel": "#DCE8F3",
    "amber": "#E7B73F",
    "teal": "#128271",
    "coral": "#D95D4F",
    "ink": "#1C2B3A",
    "muted": "#62758A",
    "surface": "#F6F8FB",
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@500&display=swap');
:root { --navy:#152E4D; --navy2:#21486F; --steel:#DCE8F3; --amber:#E7B73F;
 --teal:#128271; --coral:#D95D4F; --ink:#1C2B3A; --muted:#62758A; --surface:#F6F8FB; }
.stApp { background: var(--surface); color: var(--ink); }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"], #MainMenu, footer { visibility: hidden; }
.block-container { max-width: 1240px; padding: 2rem 2.2rem 4rem; }
h1,h2,h3,p,label,[data-testid="stWidgetLabel"] { font-family: Inter,Segoe UI,sans-serif; }
.erp-header { background:linear-gradient(112deg,#142D4B 0%,#1F456B 100%); color:white;
 border:1px solid rgba(255,255,255,.09); border-radius:16px; padding:27px 30px 25px;
 box-shadow:0 14px 34px rgba(21,46,77,.18); position:relative; overflow:hidden; margin-bottom:20px; }
.erp-header:after { content:""; position:absolute; width:220px;height:220px;right:-75px;top:-120px;
 border:34px solid rgba(231,183,63,.16);border-radius:50%; }
.eyebrow { color:#F4CB68; font-size:.72rem; letter-spacing:.15em; font-weight:700; text-transform:uppercase; }
.erp-header h1 { color:white; font-size:2rem; letter-spacing:-.025em; margin:.4rem 0 .25rem; }
.erp-header p { color:#DCE8F3; margin:0; font-size:.96rem; }
.badges { display:flex; flex-wrap:wrap; gap:8px; margin-top:17px; }
.badge { display:inline-flex;align-items:center;gap:7px;border-radius:999px;padding:6px 10px;
 font-size:.72rem;font-weight:700;letter-spacing:.035em;border:1px solid rgba(255,255,255,.18); }
.badge-amber { background:rgba(231,183,63,.16); color:#FFD978; }
.badge-teal { background:rgba(18,130,113,.2); color:#AEE9DC; }
.section-card { background:white;border:1px solid #DDE5ED;border-radius:14px;padding:20px 22px;
 box-shadow:0 5px 18px rgba(21,46,77,.055); margin:8px 0 18px; }
.section-kicker { color:#3F668C;font-size:.69rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase; }
.section-title { color:var(--navy);font-size:1.08rem;font-weight:700;margin:3px 0 12px; }
.pipeline { display:grid;grid-template-columns:repeat(5,1fr);gap:9px;margin:8px 0 20px; }
.pipe-step { background:white;border:1px solid #DDE5ED;border-radius:11px;padding:12px 12px 11px;
 box-shadow:0 3px 10px rgba(21,46,77,.04);min-height:70px; }
.pipe-num { width:21px;height:21px;border-radius:6px;background:#EDF2F7;color:#597086;display:inline-grid;
 place-items:center;font-size:.68rem;font-weight:700;margin-right:5px; }
.pipe-name { font-size:.78rem;font-weight:700;color:var(--navy); }
.pipe-state { font-size:.67rem;text-transform:uppercase;letter-spacing:.08em;color:#8090A0;margin-top:9px; }
.state-waiting { border-color:#D8E0E8;background:#FFFFFF; }
.state-waiting .pipe-state { color:#667B90; }
.state-running { border-color:#D7A72D;box-shadow:inset 0 3px 0 var(--amber); }
.state-running .pipe-state { color:#9A7414; }
.state-success { border-color:#9BD1C7;box-shadow:inset 0 3px 0 var(--teal); }
.state-success .pipe-state { color:var(--teal); }
.state-skipped { border-color:#CED6DE;background:#F0F3F6;box-shadow:inset 0 3px 0 #8997A5; }
.state-skipped .pipe-name { color:#526270; }
.state-skipped .pipe-state { color:#5C6B79; }
.state-abstained { border-color:#E7CA7A;background:#FFF9E9;box-shadow:inset 0 3px 0 var(--amber); }
.state-abstained .pipe-state { color:#82600B; }
.state-error,.state-rejected { border-color:#EDB3AC;box-shadow:inset 0 3px 0 var(--coral); }
.state-error .pipe-state,.state-rejected .pipe-state { color:var(--coral); }
.state-timeout { border-color:#E4A99F;background:#FFF5ED;box-shadow:inset 0 3px 0 var(--amber); }
.state-timeout .pipe-state { color:#B14F43; }
.metric-strip { display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:15px; }
.mini-metric { border:1px solid #E1E7ED;background:#FBFCFD;border-radius:10px;padding:12px 14px; }
.mini-label { color:var(--muted);font-size:.68rem;text-transform:uppercase;letter-spacing:.08em; }
.mini-value { color:var(--navy);font-size:1.03rem;font-weight:700;margin-top:4px; }
.notice { border-radius:10px;padding:14px 16px;border-left:4px solid #8090A0;background:#F1F4F7;color:#33475A; }
.notice-success { border-color:var(--teal);background:#EBF7F4; }
.notice-error { border-color:var(--coral);background:#FCF0EE; }
.notice-warning { border-color:var(--amber);background:#FFF8E6; }
.schema-row { display:grid;grid-template-columns:42px minmax(180px,1fr) minmax(260px,2.4fr) 80px;
 gap:12px;align-items:start;border:1px solid #E0E7EE;border-radius:10px;padding:13px 14px;margin:8px 0;background:#FCFDFE; }
.schema-rank { background:var(--navy);color:white;border-radius:7px;text-align:center;padding:5px;font-size:.75rem;font-weight:700; }
.schema-name { color:var(--navy);font:600 .78rem 'JetBrains Mono',monospace;word-break:break-word; }
.schema-summary { color:var(--muted);font-size:.78rem;line-height:1.45; }
.schema-score { color:#4F6580;font-size:.75rem;text-align:right; }
.stButton>button { border-radius:9px;min-height:42px;font-family:Inter,sans-serif;font-weight:650; }
.stButton>button[kind="primary"] { background:var(--navy);border-color:var(--navy); }
.stButton>button[kind="primary"]:hover { background:var(--navy2);border-color:var(--amber); }
[data-testid="stBaseButton-secondary"] { background:#F7F9FC !important;border-color:#AEBECB !important;color:var(--navy) !important; }
[data-testid="stBaseButton-secondary"] p { color:inherit !important; }
[data-testid="stBaseButton-secondary"]:hover:not(:disabled) { background:var(--steel) !important;border-color:#6F8EAA !important;color:#102B48 !important; }
[data-testid="stBaseButton-secondary"]:focus-visible { outline:3px solid rgba(231,183,63,.38) !important;outline-offset:2px; }
[data-testid="stBaseButton-secondary"]:disabled { opacity:1 !important;background:#34495E !important;border-color:#4C6277 !important;color:#C2CED9 !important;cursor:not-allowed; }
[data-testid="stSelectbox"] [data-testid="stWidgetLabel"],
[data-testid="stSelectbox"] [data-testid="stWidgetLabel"] p { color:#3F668C !important;font-weight:700 !important; }
[data-testid="stTextAreaRootElement"] { background:#1B324F !important;border:1px solid #66819A !important;border-radius:10px !important;box-shadow:none !important; }
[data-testid="stTextAreaRootElement"]:focus-within { border-color:var(--amber) !important;box-shadow:0 0 0 3px rgba(231,183,63,.24) !important; }
[data-testid="stTextAreaRootElement"] textarea { background:transparent !important;color:#F6F9FC !important;caret-color:#FFD76A !important;border:0 !important;border-radius:10px !important;outline:0 !important;-webkit-text-fill-color:#F6F9FC !important; }
[data-testid="stTextAreaRootElement"] textarea::placeholder { color:#B8C7D6 !important;opacity:1 !important;-webkit-text-fill-color:#B8C7D6 !important; }
[data-testid="stTextAreaRootElement"] textarea::selection { background:#F2C94C !important;color:#132D49 !important;-webkit-text-fill-color:#132D49 !important; }
[data-testid="stTextArea"] [data-testid="stCaptionContainer"],
[data-testid="stTextArea"] small { color:#586F86 !important; }
[data-testid="stTabs"] [data-testid="stTab"] { font-family:Inter,sans-serif;font-weight:650;color:#435C74 !important; }
[data-testid="stTabs"] [data-testid="stTab"] p { color:inherit !important; }
[data-testid="stTabs"] [data-testid="stTab"]:hover { color:#173F68 !important;background:#EEF3F8; }
[data-testid="stTabs"] [data-testid="stTab"][aria-selected="true"] { color:var(--navy) !important; }
[data-testid="stTabs"] .react-aria-SelectionIndicator { background-color:var(--amber) !important;height:3px !important;border-radius:3px 3px 0 0; }
[data-testid="stTabs"] [data-testid="stTab"]:focus-visible { outline:2px solid #3E6C96 !important;outline-offset:-2px; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color:#526A82 !important; }
[data-testid="stMetric"] [data-testid="stMetricLabel"],
[data-testid="stMetric"] [data-testid="stMetricLabel"] p { color:#526A82 !important; }
[data-testid="stMetric"] [data-testid="stMetricValue"],
[data-testid="stMetric"] [data-testid="stMetricValue"] div { color:var(--navy) !important; }
[data-testid="stDataFrame"] { border:1px solid #DEE6ED;border-radius:10px;overflow:hidden; }
code { font-family:'JetBrains Mono',Consolas,monospace !important; }
@media(max-width:760px){.block-container{padding:1rem}.pipeline{grid-template-columns:1fr 1fr}
 .metric-strip{grid-template-columns:1fr}.schema-row{grid-template-columns:38px 1fr}.schema-summary,.schema-score{grid-column:2}}
</style>
"""


def page_header(mode: str) -> str:
    mode_badge = "MOCK / DEVELOPMENT" if mode == "demo" else "LIVE ADAPTERS"
    return f"""<div class="erp-header"><div class="eyebrow">GALEX · Enterprise reporting</div>
    <h1>ERP Intelligence — Text to SQL</h1>
    <p>Natural-language reporting for enterprise data, with a visible safety pipeline.</p>
    <div class="badges"><span class="badge badge-amber">● {mode_badge}</span>
    <span class="badge badge-teal">◆ Read-only execution</span></div></div>"""


def pipeline_html(steps: dict[str, str]) -> str:
    labels = (("retrieval", "Retrieval"), ("reranking", "Reranking"),
              ("generation", "Generation"), ("validation", "Validation"),
              ("execution", "Execution"))
    cards = []
    for number, (key, label) in enumerate(labels, 1):
        state = steps.get(key, "waiting")
        cards.append(f'<div class="pipe-step state-{html.escape(state)}"><span class="pipe-num">{number}</span>'
                     f'<span class="pipe-name">{label}</span><div class="pipe-state">{html.escape(state)}</div></div>')
    return '<div class="pipeline">' + "".join(cards) + "</div>"


def notice(message: str, kind: str = "warning") -> str:
    return f'<div class="notice notice-{kind}">{html.escape(message)}</div>'


def schema_row(rank, name, summary, score=None) -> str:
    score_text = "—" if score is None else f"{score:.4f}"
    return (f'<div class="schema-row"><div class="schema-rank">{int(rank):02d}</div>'
            f'<div class="schema-name">{html.escape(name)}</div>'
            f'<div class="schema-summary">{html.escape(summary or "No summary provided")}</div>'
            f'<div class="schema-score">{html.escape(score_text)}</div></div>')
