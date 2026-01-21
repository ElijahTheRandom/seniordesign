import streamlit as st
import streamlit.components.v1 as components
 
print("Loading homepage.py") 

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

    /* Force full white background */
    .stApp {
        background-color: white;
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


# Disable scrolling
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

st.markdown(
    """
    <style>
    /* Full-app background gradient */
    .stApp {
        background: linear-gradient(
            90deg,
            #f8fafc 0%,
            #eef2ff 40%,
            #ffffff 70%,
            #ffffff 100%
        );
    }

    /* Ensure no white bleed from body */
    html, body {
        background: transparent;
        margin: 0;
        padding: 0;
    }
    </style>
    """,
    unsafe_allow_html=True
)

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

# HTML and CSS for the homepage
components.html(
    """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<link href="https://fonts.googleapis.com/css2?family=Cantora+One&display=swap" rel="stylesheet">

<style>
:root {
  --bg:#ffffff;
  --text:#0f172a;
  --muted:#64748b;
  --border:#e5e7eb;
  --accent:#2563eb;
}
* { box-sizing: border-box; }

body {
  margin:0;
  padding:0;
  font-family:'Cantora One', serif;
  background:var(--bg);
  color:var(--text);
  height:100vh;
  width:100vw;
  overflow:hidden;
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
  background:linear-gradient(135deg,#f8fafc,#eef2ff);
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
  animation: float 6s ease-in-out infinite, fade 10s ease-in-out infinite;
}

.panel:nth-child(2){animation-delay:2s;}
.panel:nth-child(3){animation-delay:4s;}
.panel:nth-child(4){animation-delay:6s;}
.panel:nth-child(5){animation-delay:8s;}

@keyframes float {
  0%,100% { transform:translateY(0); }
  50% { transform:translateY(-20px); }
}
@keyframes fade {
  0%,100% { opacity:.5; }
  50% { opacity:1; }
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
  background:conic-gradient(var(--accent) 65%, #e5e7eb 0%);
  margin:12px auto;
}
.sparkline {
  height:40px;
  background:linear-gradient(90deg,
    rgba(37,99,235,.2),
    rgba(37,99,235,.6),
    rgba(37,99,235,.2));
  border-radius:8px;
}
.line {
  height:100px;
  background:linear-gradient(180deg,
    rgba(37,99,235,.25),
    rgba(37,99,235,0));
  border-radius:10px;
}

/* POSITIONS */
.chart-panel {top:60px;left:80px;width:220px;}
.table-panel {top:260px;left:40px;width:260px;}
.line-panel {top:140px;left:340px;width:240px;}
.donut-panel {top:360px;left:320px;width:180px;}
.spark-panel {top:40px;left:360px;width:200px;}

.table {
  width:100%;
  border-collapse:collapse;
  font-size:14px;
}

/* RIGHT CONTENT */
.content {
  padding:80px 72px;
  display:flex;
  flex-direction:column;
  justify-content:center;
  animation:fadeIn 2s ease-in-out;
}
.eyebrow {
  font-size:13px;
  letter-spacing:.08em;
  text-transform:uppercase;
  color:var(--muted);
  margin-bottom:16px;
  animation:fadeIn 2s ease-in-out;
}
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
h1 {
  font-family:"Cantora One",serif;
  font-size:clamp(36px,4vw,52px);
  margin:0 0 24px;
}
p {
  color:var(--muted);
  font-size:18px;
  max-width:480px;
}
.cta button {
  margin-top:36px;
  padding:14px 32px;
  font-size:15px;
  font-weight:600;
  border-radius:8px;
  border:1px solid var(--text);
  background:transparent;
  cursor:pointer;
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
    <strong>Distribution</strong>
    <div class="chart">
      <div class="bar" style="height:40%"></div>
      <div class="bar" style="height:70%"></div>
      <div class="bar" style="height:55%"></div>
      <div class="bar" style="height:85%"></div>
      <div class="bar" style="height:60%"></div>
    </div>
  </div>

  <div class="panel table-panel">
    <strong>Summary</strong>
    <table class="table">
      <tr><th>Mean</th><td>42.6</td></tr>
      <tr><th>Median</th><td>41.0</td></tr>
      <tr><th>Std Dev</th><td>6.2</td></tr>
    </table>
  </div>

  <div class="panel line-panel">
    <strong>Trend</strong>
    <div class="line"></div>
  </div>

  <div class="panel donut-panel">
    <strong>Completion</strong>
    <div class="donut"></div>
  </div>

  <div class="panel spark-panel"> 
    <strong>Signal</strong>
    <div class="sparkline"></div>
  </div>
</section>

<section class="content">
  <div class="eyebrow"></div>
  <h1>Powerful statistical analysis,<br/> beautifully visualized</h1>
  <p>
    Analyze datasets, explore trends, and understand your numbers with
    clean charts, clear tables, and intuitive tools built for insight.
  </p>
  <div class="cta">
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
