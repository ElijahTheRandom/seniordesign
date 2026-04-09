import streamlit as st
import streamlit.components.v1 as components
import os
import base64
import json
from pathlib import Path
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def _img_to_b64(filename: str) -> str:
    path = Path(BASE_DIR) / "pages" / "assets" / filename
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

_favicon_icons = json.dumps([
    _img_to_b64("ps_main_man.png"),
    _img_to_b64("ElijahSquirrel.png"),
    _img_to_b64("AshtonSquirrel.png"),
    _img_to_b64("ChrisSquirrel.png"),
    _img_to_b64("HyattSquirrel.png"),
    _img_to_b64("SamSquirrel.png"),
])

st.set_page_config(
    page_title="PS Analytics",
    layout="wide",
    page_icon=Image.open(Path(BASE_DIR) / "pages" / "assets" / "ps_main_man.png")
)

st.markdown("""
<style>
html, body, .stApp, * { font-family: "Source Sans Pro", sans-serif !important; }
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.block-container {
    padding-top: 0rem; padding-bottom: 0rem;
    padding-left: 0rem; padding-right: 0rem;
    max-width: 100%;
}
section.main > div { padding-top: 0rem !important; }
html, body {
    margin: 0; height: 100%; width: 100%; padding: 0;
    overflow: hidden !important; overscroll-behavior: none;
    background-color: #000000 !important;
}
.stApp, .stAppViewContainer, [data-testid="stAppViewContainer"],
section.main, section.main > div {
    height: 100vh !important; overflow: hidden !important;
}
.stApp { background-color: #000000 !important; }
iframe { overflow: hidden !important; border: none; }
div[data-testid="stVerticalBlock"] { overflow: hidden !important; gap: 0rem !important; }
div[data-testid="stVerticalBlock"] > div { margin-top: 0 !important; padding-top: 0 !important; }
</style>
""", unsafe_allow_html=True)

clicked = st.button("Get Started", key="real_button", use_container_width=True)

if clicked:
    st.switch_page("pages/mainpage.py")

st.markdown("""
<style>
iframe { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; border: none; overflow: hidden; }
:root { --cta-width: 200px; }
div[data-testid="stButton"] {
    position: fixed !important; left: 54.5%; top: 65%;
    transform: translateX(-50%) translateZ(0); will-change: transform;
    z-index: 9999; width: 220px !important; max-width: 220px !important;
    min-width: 220px !important; transition: left 0.35s ease, top 0.35s ease;
    opacity: 0; animation: buttonFadeIn 1s ease-out forwards; animation-delay: 1.2s;
}
div[data-testid="stButton"] > div { width: 220px !important; }
div[data-testid="stButton"] button {
    background: linear-gradient(135deg, rgba(228,120,29,0.18), rgba(228,120,29,0.10)) !important;
    border: 1.5px solid rgba(228,120,29,0.55) !important; border-radius: 10px !important;
    color: rgba(255,255,255,0.92) !important; font-weight: 600 !important;
    padding: 12px 20px !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.35), 0 0 18px rgba(228,120,29,0.25), inset 0 1px 2px rgba(255,255,255,0.05) !important;
    transition: transform 0.15s ease, box-shadow 0.2s ease;
    transform: translateZ(0); backface-visibility: hidden; will-change: transform;
}
div[data-testid="stButton"] button:hover {
    transform: translateY(-2px) translateZ(0);
    box-shadow: 0 6px 20px rgba(0,0,0,0.45), 0 0 25px rgba(228,120,29,0.35) !important;
}
div[data-testid="stButton"] button,
div[data-testid="stButton"] button:active,
div[data-testid="stButton"] button:focus,
div[data-testid="stButton"] button:focus-visible,
div[data-testid="stButton"] button:visited {
    background: linear-gradient(135deg, rgba(228,120,29,0.18), rgba(228,120,29,0.10)) !important;
    border: 1.5px solid rgba(228,120,29,0.55) !important;
    color: rgba(255,255,255,0.92) !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.35), 0 0 18px rgba(228,120,29,0.25), inset 0 1px 2px rgba(255,255,255,0.05) !important;
    outline: none !important;
}
div[data-testid="stButton"] button:active { transform: translateY(1px) translateZ(0) !important; }
@keyframes buttonFadeIn {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}
div[data-testid="stButton"] button span,
div[data-testid="stButton"] button div span,
div[data-testid="stButton"] button * { font-weight: 545 !important; }
@media (max-width: 1150px) {
    div[data-testid="stButton"] { left: 22% !important; top: 65% !important; transform: translateX(-50%) !important; }
}
</style>
""", unsafe_allow_html=True)

components.html(
    f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@300;400;600;700&display=swap" rel="stylesheet" media="print" onload="this.media='all'">
<style>
* {{ font-family: "Source Sans Pro", sans-serif !important; }}
:root {{
  --bg:#ffffff; --text:#0f172a; --muted:#64748b;
  --border:#e5e7eb; --accent:#e4781d;
  --accent-20: rgba(246,51,102,0.20);
  --accent-60: rgba(246,51,102,0.60);
  --accent-25: rgba(246,51,102,0.25);
}}
* {{ box-sizing: border-box; }}
hr {{
    border: none !important; height: 1px !important;
    background: linear-gradient(90deg, transparent 0%, rgba(228,120,29,0.5) 50%, transparent 100%) !important;
    margin: 2rem 0 !important;
}}
body {{
  margin:0; padding:0;
  background: radial-gradient(ellipse at top, #1a1a1a 0%, #0f0f0f 50%, #000000 100%) !important;
  color: white !important; height:100vh; width:100vw; overflow:hidden;
}}
.layout {{
  animation: fadeIn 1s ease-in-out; animation-delay: 0s;
  opacity: 0; animation-fill-mode: forwards;
  display:grid; grid-template-columns:1fr auto 1fr;
  height: 100vh; width: 100vw; overflow:hidden; margin:0; padding:0;
}}
.visual {{
  position:relative; height:100vh; width:100%;
  background: transparent !important; overflow:hidden;
  padding:48px; margin:0; box-sizing:border-box;
}}
.panel {{
  opacity: 0.25; will-change: opacity, transform; position: absolute;
  border: 1.5px solid rgba(228,120,29,0.45) !important;
  box-shadow: 0 0 12px rgba(228,120,29,0.25), 0 0 24px rgba(228,120,29,0.15), inset 0 0 4px rgba(255,255,255,0.08) !important;
  border-radius: 16px !important; padding: 16px;
  height: 180px; display: flex; flex-direction: column;
  justify-content: flex-start; gap: 8px;
}}
.chart-body {{ flex: 1; display: flex; align-items: center; justify-content: center; }}
@keyframes idleFloat {{
  0%   {{ transform: translateY(-10px); }}
  50%  {{ transform: translateY(-20px); }}
  100% {{ transform: translateY(-10px); }}
}}
@keyframes spotlight {{
  0%   {{ opacity: 0.25; }} 25%  {{ opacity: 1; }}
  40%  {{ opacity: 0.25; }} 100% {{ opacity: 0.25; }}
}}
.mini-underline {{
    width: 60px; height: 3px;
    background: linear-gradient(90deg, #e4781d 0%, rgba(228,120,29,0.5) 70%, transparent 100%);
    border-radius: 2px; margin-top: 6px; margin-bottom: 8px;
}}
.v-divider {{
    width: 2px; height: 100%;
    background: linear-gradient(180deg, transparent 0%, var(--accent) 40%, var(--accent) 60%, transparent 100%);
    border-radius: 2px;
    box-shadow: 0 0 12px rgba(228,120,29,0.35), 0 0 24px rgba(228,120,29,0.15);
}}
.bar, .hbar, .dot, .line-point {{ box-shadow: 0 0 12px rgba(228,120,29,0.35) !important; }}
.chart {{ display:flex; align-items:flex-end; gap:8px; height:120px; }}
.bar {{ width:16px; background:var(--accent); border-radius:4px 4px 0 0; }}
.donut {{
  width:80px; height:80px; border-radius:50%;
  background:conic-gradient(var(--accent) 65%, var(--border) 0%); margin:12px auto;
}}
.scatter {{ position: relative; width: 100%; height: 100px; background: transparent; border-radius: 10px; }}
.dot {{ position: absolute; width: 10px; height: 10px; background: var(--accent); border-radius: 50%; }}
.chart-panel {{ top:5%; left:5%; width:40%; animation: idleFloat 6s ease-in-out infinite -1s, spotlight 12s ease-in-out infinite 0s; }}
.table-panel {{ top:65%; left:5%; width:40%; animation: idleFloat 6s ease-in-out infinite -9s, spotlight 12s ease-in-out infinite 8s; }}
.line-panel  {{ top:5%; left:50%; width:40%; animation: idleFloat 6s ease-in-out infinite -3s, spotlight 12s ease-in-out infinite 2s; }}
.donut-panel {{ top:35%; left:5%; width:40%; animation: idleFloat 6s ease-in-out infinite -5s, spotlight 12s ease-in-out infinite 4s; }}
.spark-panel {{ top:35%; left:50%; width:40%; animation: idleFloat 6s ease-in-out infinite -7s, spotlight 12s ease-in-out infinite 6s; }}
.trend-panel {{ top:65%; left:50%; width:40%; animation: idleFloat 6s ease-in-out infinite -11s, spotlight 12s ease-in-out infinite 10s; }}
.table {{ width:100%; border-collapse:collapse; font-size:14px; }}
.content {{ margin-top: -10px !important; padding:80px 72px; display:flex; flex-direction:column; justify-content:center; }}
.eyebrow {{ font-size:13px; letter-spacing:.08em; text-transform:uppercase; color: white !important; margin-bottom: 6px; }}
@keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
h1 {{ font-size:clamp(36px,4vw,52px); margin: 0 0 5px; color: white !important; }}
p {{ color: white !important; font-size:18px; max-width:480px; }}
h1, p, .eyebrow {{ text-shadow: 0 2px 8px rgba(0,0,0,0.4) !important; }}
.hbar-chart {{
  display: flex; flex-direction: column; justify-content: flex-start;
  gap: 8px; height: auto; padding: 10px;
  background: linear-gradient(180deg, rgba(228,120,29,0.25), rgba(228,120,29,0));
  border-radius: 10px;
}}
.hbar {{ height: 16px; background: var(--accent); border-radius: 4px; }}
.line-graph {{ position: relative; width: 100%; height: 120px; background: transparent; border-radius: 10px; }}
.line-point {{
  position: absolute; width: 10px; height: 10px;
  background: var(--accent); border-radius: 50%; transform: translate(-50%, -50%);
}}
.line-path {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; }}
.faded-bg {{
  background: linear-gradient(180deg, rgba(228,120,29,0.25), rgba(228,120,29,0.05)) !important;
  border-radius: 10px !important;
  box-shadow: 0 4px 12px rgba(0,0,0,0.35), 0 0 12px rgba(228,120,29,0.15) !important;
}}
@media (max-width: 1150px) {{
  .visual {{ display: none !important; }}
  .v-divider {{ display: none !important; }}
  .layout {{ grid-template-columns: 1fr !important; }}
  .content {{ width: 100% !important; padding: 80px 48px !important; }}
  div[data-testid="stButton"] {{ left: 50% !important; top: 70% !important; }}
}}
</style>
</head>
<body>
<div class="layout">

<section class="visual">
  <div class="panel chart-panel">
    <strong>Vertical Bar Charts</strong>
    <div class="chart-body faded-bg">
      <div class="chart">
        <div class="bar" style="height:40%"></div>
        <div class="bar" style="height:70%"></div>
        <div class="bar" style="height:55%"></div>
        <div class="bar" style="height:85%"></div>
        <div class="bar" style="height:60%"></div>
        <div class="bar" style="height:75%"></div>
        <div class="bar" style="height:30%"></div>
      </div>
    </div>
  </div>

  <div class="panel table-panel">
    <strong>Results</strong>
    <div class="chart-body faded-bg">
      <table class="table">
        <tr><th>Mean:</th><td>42.6</td></tr>
        <tr><th>Median:</th><td>41.0</td></tr>
        <tr><th>Std Dev:</th><td>6.2</td></tr>
        <tr><th>Variance:</th><td>38.4</td></tr>
        <tr><th>Mode:</th><td>5.7</td></tr>
      </table>
    </div>
  </div>

  <div class="panel line-panel">
    <strong>Scatter Plots</strong>
    <div class="chart-body faded-bg">
      <div class="scatter">
        <div class="dot" style="left:20%; top:60%"></div>
        <div class="dot" style="left:25%; top:40%"></div>
        <div class="dot" style="left:45%; top:50%"></div>
        <div class="dot" style="left:65%; top:30%"></div>
        <div class="dot" style="left:85%; top:50%"></div>
        <div class="dot" style="left:35%; top:60%"></div>
        <div class="dot" style="left:50%; top:10%"></div>
        <div class="dot" style="left:55%; top:50%"></div>
        <div class="dot" style="left:65%; top:50%"></div>
        <div class="dot" style="left:40%; top:70%"></div>
      </div>
    </div>
  </div>

  <div class="panel donut-panel">
    <strong>Pie Charts</strong>
    <div class="chart-body faded-bg">
      <div class="donut"></div>
    </div>
  </div>

  <div class="panel spark-panel">
    <strong>Horizontal Bar Charts</strong>
    <div class="hbar-chart">
      <div class="hbar" style="width: 40%"></div>
      <div class="hbar" style="width: 70%"></div>
      <div class="hbar" style="width: 55%"></div>
      <div class="hbar" style="width: 85%"></div>
      <div class="hbar" style="width: 60%"></div>
    </div>
  </div>

  <div class="panel trend-panel">
    <strong>Line Graphs</strong>
    <div class="chart-body faded-bg">
      <div class="line-graph">
        <div class="line-point" style="left:5%; top:60%"></div>
        <div class="line-point" style="left:20%; top:50%"></div>
        <div class="line-point" style="left:35%; top:55%"></div>
        <div class="line-point" style="left:50%; top:40%"></div>
        <div class="line-point" style="left:65%; top:45%"></div>
        <div class="line-point" style="left:80%; top:30%"></div>
        <div class="line-point" style="left:95%; top:40%"></div>
        <svg class="line-path">
          <polyline points="5,75 270,40" stroke="#e4781d" stroke-width="3" fill="none"/>
        </svg>
      </div>
    </div>
  </div>
</section>

<div class="v-divider"></div>

<section class="content">
  <div class="eyebrow">Powered by Group 6</div>
  <h1>PS Analytics<br/></h1>
  <div class="mini-underline"></div>
  <p>
    Your go-to tool for statistical analytics.
    <br>Import files, edit tables, visualize datasets,
    compare results, and export your reports all on one platform.
  </p>
</section>

</div>

<script>
(function() {{
    const icons = {_favicon_icons};
    let i = 0;

    function rotateFavicon() {{
        let link = window.parent.document.querySelector("link[rel~='icon']");
        if (!link) {{
            link = window.parent.document.createElement("link");
            link.rel = "icon";
            window.parent.document.head.appendChild(link);
        }}
        link.type = "image/png";
        link.href = "data:image/png;base64," + icons[i % icons.length];
        i++;
    }}

    rotateFavicon();
    setInterval(rotateFavicon, 1000);
}})();
</script>

</body>
</html>
""",
    scrolling=False
)