# streamlit_hidden_page = True
import streamlit as st
import streamlit.components.v1 as components
import os

# Debug print
print("Loading homepage.py...") 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Set page configuration
st.set_page_config(
    page_title="PS Analytics",
    page_icon=os.path.join(BASE_DIR, "pages/assets", "PStheMainMan.png"),
    layout="wide"
)

st.markdown(
"""
<style>
html, body, .stApp, * {
    font-family: "Source Sans Pro", sans-serif !important;
}
</style>
""",
unsafe_allow_html=True
)

# Hide Streamlit chrome
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True
)

# Remove default padding/margin
st.markdown(
    """
    <style>
    /* Remove default Streamlit padding */
    .block-container {
        padding-top: 0rem;
        padding-bottom: 0rem;
        padding-left: 0rem;
        padding-right: 0rem;
        max-width: 100%;
    }

    section.main > div {
    padding-top: 0rem !important;
    }


    /* Remove margin around body */
    html, body {
        margin: 0;
        height: 100%;
        width: 100%;
        padding: 0;
        background-color: white;
    }

    * {
    font-family: "Source Sans Pro", sans-serif !important;
}
    </style>
    """,
    unsafe_allow_html=True
)

# Prevent scrolling
st.markdown(
    """
    <style>
    /* Lock viewport completely */
    html, body {
        height: 100%;
        overflow: hidden;
        overscroll-behavior: none;
    }

    /* Kill Streamlit's internal scroll container */
    .stApp,
    .stAppViewContainer,
    section.main {
        height: 100vh !important;
        overflow: hidden !important;
    }

    /* Prevent iframe from introducing scroll */
    iframe {
        overflow: hidden !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# More scroll blocking
st.markdown("""
<style>
/* Kill all scrolling */
html, body {
    height: 100%;
    overflow: hidden;
}

/* Ensure Streamlit app does not scroll */
.stApp {
    overflow: hidden;
}

/* Remove iframe padding */
iframe {
    border: none;
}
</style>
""", unsafe_allow_html=True)

# Set black background
st.markdown(
    """
    <style>
    .stApp {
        background-color: #000000 !important;
    }

    html, body {
        background-color: #000000 !important;
        margin: 0;
        padding: 0;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Adjust spacing
st.markdown(
    """
    <style>
    /* Kill vertical gap added by Streamlit layout blocks */
    div[data-testid="stVerticalBlock"] {
        gap: 0rem !important;
    }

    /* Ensure no extra spacing sneaks in */
    div[data-testid="stVerticalBlock"] > div {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown("""
<style>
html, body {
    margin: 0;
    padding: 0;
    height: 100%;
    overflow: hidden;
}

.stApp,
[data-testid="stAppViewContainer"],
section.main,
section.main > div {
    height: 100vh;
    overflow: hidden;
}

iframe {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    border: none;
    overflow: hidden;
}
</style>
""", unsafe_allow_html=True)

# REAL Streamlit button (must stay BEFORE the iframe)
st.markdown( 
    """ 
    <style> 
    :root {
      --cta-width: 200px;
    }
    </style> 
    """, 
    unsafe_allow_html=True 
    )

# Button styling like Run Analysis
st.markdown("""
<style>
div[data-testid="stButton"] button {
    background: linear-gradient(135deg, rgba(228,120,29,0.18), rgba(228,120,29,0.10)) !important;
    border: 1.5px solid rgba(228,120,29,0.55) !important;
    border-radius: 10px !important;
    color: rgba(255,255,255,0.92) !important;
    font-weight: 600 !important;
    padding: 12px 20px !important;
    box-shadow:
        0 4px 12px rgba(0,0,0,0.35),
        0 0 18px rgba(228,120,29,0.25),
        inset 0 1px 2px rgba(255,255,255,0.05) !important;
    transition: all 0.2s ease !important;
}

div[data-testid="stButton"] button:hover {
    background: rgba(228,120,29,0.25) !important;
    border-color: rgba(228,120,29,0.7) !important;
    transform: translateY(-2px) !important;
    box-shadow:
        0 6px 20px rgba(0,0,0,0.45),
        0 0 25px rgba(228,120,29,0.35) !important;
}

    transition:
        background-color 0.15s ease,
        box-shadow 0.15s ease,
        transform 0.12s ease;
}

div[data-testid="stButton"] button:hover,
div[data-testid="stFileUploader"] button:hover {
    background-color: #e4781d !important;
    border-color: #e4781d !important;

    box-shadow:
        0 4px 12px rgba(214, 107, 29, 0.45),
        0 0 0 3px rgba(214, 107, 29, 0.35);

    transform: translateY(-1px);
}

div[data-testid="stButton"] button:active,
div[data-testid="stFileUploader"] button:active {
    background-color: #b85b18 !important;
    border-color: #b85b18 !important;
    transform: translateY(0);
}

div[data-testid="stButton"] button:focus-visible,
div[data-testid="stFileUploader"] button:focus-visible {
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(214, 107, 29, 0.5);
}
</style>
""", unsafe_allow_html=True)

st.markdown(
"""
<style>
@keyframes buttonFadeIn {
    from {
        opacity: 0;
        transform: translateY(8px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

div[data-testid="stButton"] {
  position: fixed !important;

  /* RESPONSIVE POSITION */
  right: 31vw;        /* moves with screen size */
  top: 65%;

  width: 220px !important;
  max-width: 220px !important;
  min-width: 220px !important;
  z-index: 9999;
}

/* Keep Streamlit from stretching it */
div[data-testid="stButton"] > div {
  width: 220px !important;
}

div[data-testid="stButton"] {
  opacity: 0;
  animation: buttonFadeIn 1s ease-out forwards;
  animation-delay: 1.2s;
}
</style>
""",
unsafe_allow_html=True
)

st.markdown(
"""
<style>
/* Hide button when viewport is narrow (split screen) */
@media (max-width: 1200px) {
    div[data-testid="stButton"] {
        display: none !important;
    }
}
</style>
""",
unsafe_allow_html=True
)

clicked = st.button( 
    "Get Started", 
    key="real_button", 
    use_container_width=True 
) 

# Redirect to mainpage.py on click 
if clicked: 
  st.switch_page("pages/mainpagecopy.py")

# HTML and CSS for the homepage all fake charts, layout, and movement, etc.
components.html(
    """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">

<!-- LOAD SOURCE SANS PRO FOR THE IFRAME -->
<link href="https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@300;400;600;700&display=swap" rel="stylesheet">

<style>
/* APPLY THE FONT TO EVERYTHING INSIDE THE IFRAME */
* {
    font-family: "Source Sans Pro", sans-serif !important;
}
:root {
  --bg:#ffffff;
  --text:#0f172a;
  --muted:#64748b;
  --border:#e5e7eb;
  --accent:#e4781d;

  --accent-20: rgba(246,51,102,0.20);
  --accent-60: rgba(246,51,102,0.60);
  --accent-25: rgba(246,51,102,0.25);
}
* { box-sizing: border-box; }

hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, 
        transparent 0%, 
        rgba(228,120,29,0.5) 50%, 
        transparent 100%) !important;
    margin: 2rem 0 !important;
}

body {
  margin:0;
  padding:0;
  background: radial-gradient(ellipse at top, #1a1a1a 0%, #0f0f0f 50%, #000000 100%) !important;
  color: white !important;
  color:var(--text);
  height:100vh;
  width:100vw;
  overflow:hidden;
}

.layout {
  animation: fadeIn 1s ease-in-out;
  animation-delay: 0s;
  opacity: 0;
  animation-fill-mode: forwards;
}

.layout {
  display:grid;
  grid-template-columns:1fr auto 1fr;
  height: 100vh;
  width: 100vw;
  overflow:hidden;
  margin:0;
  padding:0;
}

/* LEFT VISUAL */
.visual {
  position:relative;
  height:100vh;
  width:100%;
  background: transparent !important;
  overflow:hidden;
  padding:48px;
  margin:0;
  box-sizing:border-box;
}

/* FLOATING PANELS */
.panel {
  position: absolute;
  background: rgba(20, 20, 20, 0.55) !important;
  border: 1px solid rgba(255, 255, 255, 0.08) !important;
  border-radius: 16px !important;
  backdrop-filter: blur(18px) saturate(180%) !important;
  box-shadow:
    0 8px 32px rgba(0,0,0,0.45),
    inset 0 1px 0 rgba(255,255,255,0.05),
    0 0 20px rgba(0,0,0,0.35) !important;

  /* NEW OUTLINE + GLOW */ 
  border: 1.5px solid rgba(228,120,29,0.45) !important; 
  box-shadow: 
    0 0 12px rgba(228,120,29,0.25), 
    0 0 24px rgba(228,120,29,0.15), 
    inset 0 0 4px rgba(255,255,255,0.08) !important;
  padding: 16px;
  opacity: 1 !important;

  height: 180px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: 8px;

  animation:
    idleFloat 6s ease-in-out infinite,
    spotlight 12s ease-in-out infinite;
}

body {
  animation: none;
}

/* Spotlight order */
.chart-panel  { animation-delay: -1s, 0s; }
.line-panel   { animation-delay: -3s, 2s; }
.donut-panel  { animation-delay: -5s, 4s; }
.spark-panel  { animation-delay: -7s, 6s; }
.table-panel  { animation-delay: -9s, 8s; }
.trend-panel  { animation-delay: -11s,10s; }

.chart-body {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

@keyframes idleFloat {
  0%   { transform: translateY(-10px); }
  50%  { transform: translateY(-20px); }
  100% { transform: translateY(-10px); }
}

@keyframes dividerPulse {
    0% { box-shadow: 0 0 12px rgba(228,120,29,0.25); }
    50% { box-shadow: 0 0 20px rgba(228,120,29,0.45); }
    100% { box-shadow: 0 0 12px rgba(228,120,29,0.25); }
}

@keyframes spotlight {
  0%   { opacity: 0.25; }
  25%  { opacity: 1; }
  40%  { opacity: 0.25; }
  100% { opacity: 0.25; }
}

/* CHARTS */
.mini-underline {
    width: 60px;
    height: 3px;
    background: linear-gradient(90deg, #e4781d 0%, rgba(228,120,29,0.5) 70%, transparent 100%);
    border-radius: 2px;
    margin-top: 6px;
    margin-bottom: 8px;
}
.v-divider {
    width: 2px;
    height: 100%;
    background: linear-gradient(
        180deg,
        rgba(228,120,29,0) 0%,
        rgba(228,120,29,0.45) 40%,
        rgba(228,120,29,0.75) 50%,
        rgba(228,120,29,0.45) 60%,
        rgba(228,120,29,0) 100%
    );
    border-radius: 2px;
    animation: dividerPulse 4s ease-in-out infinite;
    box-shadow:
        0 0 12px rgba(228,120,29,0.35),
        0 0 24px rgba(228,120,29,0.15),
        inset 0 0 4px rgba(255,255,255,0.15);
}

.bar, .hbar, .dot, .line-point {
    box-shadow: 0 0 12px rgba(228,120,29,0.35) !important;
}
.chart {
  display:flex;
  align-items:flex-end;
  gap:8px;
  height:120px;
}
.bar {
  width:16px;
  background:var(--accent);
  border-radius:4px 4px 0 0;
}
.donut {
  width:80px;
  height:80px;
  border-radius:50%;
  background:conic-gradient(var(--accent) 65%, var(--border) 0%);
  margin:12px auto;
}

.sparkline {
  height:40px;
  background:linear-gradient(
    90deg,
    rgba(228,120,29,0.20),
    rgba(228,120,29,0.60),
    rgba(228,120,29,0.20)
  );
  border-radius:8px;
}

.scatter {
  position: relative;
  width: 100%;
  height: 100px;
  background: transparent;
  border-radius: 10px;
}

.dot {
  position: absolute;
  width: 10px;
  height: 10px;
  background: var(--accent);
  border-radius: 50%;
}

/* POSITIONS */
.chart-panel { top:5%; left:5%; width:40%; }
.table-panel { top:65%; left:5%; width:40%; }
.line-panel { top:5%; left:50%; width:40%; }
.donut-panel { top:35%; left:5%; width:40%; }
.spark-panel { top:35%; left:50%; width:40%; }
.trend-panel { top:65%; left:50%; width:40%; }

.table {
  width:100%;
  border-collapse:collapse;
  font-size:14px;
}

/* RIGHT CONTENT */
.content {
  margin-top: -10px !important;
  padding:80px 72px;
  display:flex;
  flex-direction:column;
  justify-content:center;
}
.eyebrow {
  font-size:13px;
  letter-spacing:.08em;
  text-transform:uppercase;
  color: white !important;
  margin-bottom: 6px;
}
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
h1 {
  font-size:clamp(36px,4vw,52px);
  margin: 0 0 10px;
  margin-bottom: 5px;
  color: white !important;
}
p {
  color: white !important;
  font-size:18px;
  max-width:480px;
}
h1, p, .eyebrow {
    text-shadow: 0 2px 8px rgba(0,0,0,0.4) !important;
}

.hbar-chart {
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: 8px;
  height: auto;
  padding: 10px;
  background: linear-gradient(
    180deg,
    rgba(228,120,29,0.25),
    rgba(228,120,29,0)
  );
  border-radius: 10px;
}

.hbar {
  height: 16px;
  background: var(--accent);
  border-radius: 4px;
}

.trend-panel {
  top: 65%;
  left: 50%;
  width: 40%;
}

.line-graph {
  position: relative;
  width: 100%;
  height: 120px;
  background: transparent;
  border-radius: 10px;
}

.line-point {
  position: absolute;
  width: 10px;
  height: 10px;
  background: var(--accent);
  border-radius: 50%;
  transform: translate(-50%, -50%);
}

.line-path {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.faded-bg {
  background: linear-gradient(
      180deg,
      rgba(228,120,29,0.25),
      rgba(228,120,29,0.05)
  ) !important;
  border-radius: 10px !important;
  box-shadow:
      0 4px 12px rgba(0,0,0,0.35),
      0 0 12px rgba(228,120,29,0.15) !important;
}

@media(max-width:900px){
  .layout{grid-template-columns:1fr;}
  .visual{min-height:420px;}
}
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
          <polyline 
            points="5,75 270,40"
            stroke="#e4781d"
            stroke-width="3"
            fill="none"
          />
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
</body>
</html>
""",
height=0,
scrolling=False
)

st.markdown("""
<style>
/* FINAL SCROLL KILL — DO NOT DUPLICATE ELSEWHERE */

/* Root */
html, body {
    height: 100%;
    overflow: hidden !important;
    overscroll-behavior: none;
}

/* Streamlit root containers */
.stApp,
[data-testid="stAppViewContainer"],
section.main,
section.main > div {
    height: 100vh !important;
    overflow: hidden !important;
}

/* Remove internal scrollbars */
div[data-testid="stVerticalBlock"] {
    overflow: hidden !important;
}

/* Iframes must never scroll */
iframe {
    overflow: hidden !important;
}
</style>
""", unsafe_allow_html=True)

