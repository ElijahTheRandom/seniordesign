import streamlit as st
import streamlit.components.v1 as components
 
# Debug print
print("Loading homepage.py") 

# Set page configuration
st.set_page_config(
    page_title="Statistical Analyzer",
    layout="wide",
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

# REAL Streamlit button (must stay BEFORE the iframe)
clicked = st.button("Get Started", key="real_button")

# Redirect to mainpage.py on click
if clicked:
    st.switch_page("pages/mainpage.py")

# Invisible button so HTML one still looks nice but this one handles movement
st.markdown("""
<style>
div[data-testid="stButton"] {
    position: absolute;
    top: 430px;
    left: 838px;
    width: 147px;
    z-index: 9999;
}
            
div[data-testid="stButton"] > button {
    height: 47px;
    background: transparent;
    color: transparent;
    border: none;
    cursor: pointer;
    pointer-events: none;
}

div[data-testid="stButton"] > button {
    pointer-events: auto;
}
            
.cta button {
  margin-top:36px;
  padding:14px 32px;
  font-size:15px;
  font-weight:600;
  border-radius:8px;

  background: #e4781d !important;   /* Streamlit primary color */
  color: white !important;                /* Streamlit button text */
  border: none !important;                /* Streamlit removes borders */

  cursor:pointer;
  transition: background 0.2s ease;
}

.cta button:hover {
  background: #d66b1d !important;         /* darker version of #F63366 */
}

</style>
""", unsafe_allow_html=True)

# HTML and CSS for the homepage all fake charts, layout, and movement, etc.
components.html(
    """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">

<style>
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

body {
  margin:0;
  padding:0;
  font-family: "Source Sans Pro", sans-serif !important;
  background:transparent !important;
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
  grid-template-columns:1fr 1fr;
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
  background:#262730 !important;
  overflow:hidden;
  padding:48px;
  margin:0;
  box-sizing:border-box;
}

/* FLOATING PANELS */
.panel {
  position:absolute;
  background:white;
  border:1px solid var(--border);
  border-radius:14px;
  box-shadow:0 20px 40px rgba(0,0,0,0.08);
  padding:16px;
  opacity: 0.25;

  animation:
    idleFloat 6s ease-in-out infinite,
    spotlight 12s ease-in-out infinite;
}

body {
  animation: none;
}

.panel {
  height: 180px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: 8px;
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


@keyframes spotlight {
  0%   { opacity: 0.25; }
  25%  { opacity: 1; }
  40%  { opacity: 0.25; }
  100% { opacity: 0.25; }
}

/* CHARTS */
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
  font-family: "Source Sans Pro", sans-serif !important;
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

.cta button {
  margin-top:36px;
  padding:14px 32px;
  font-size:15px;
  font-weight:600;
  border-radius:8px;

  background: #e4781d !important;
  color: white !important;
  border: none !important;

  cursor:pointer;
  transition: background 0.2s ease;
}

.cta button:hover {
  background: #d66b1d !important;
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
    rgba(228,120,29,0)
  );
  border-radius: 10px;
  padding: 10px;
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
            points="5,75 240,40"
            stroke="#e4781d"
            stroke-width="3"
            fill="none"
          />
        </svg>
      </div>
    </div>
  </div>
</section>

<section class="content">
  <div class="eyebrow">Powered by Group 6</div>
  <h1>PS Analytics<br/></h1>
  <p>
    Your go-to tool for statistical analytics.
    <br>Import files, edit tables, visualize datasets,
     compare results, and export your reports all on one platform.
  </p>
  <div class="cta" style="position: relative;">
    <button>Get Started</button>
  </div>  
</section>

</div>
</body>
</html>
""",
    height=740,
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

