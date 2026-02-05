import streamlit as st
import pandas as pd
import uuid
import base64
import html
import os
import io

BASE_DIR = os.path.dirname(__file__)

from PIL import Image
from streamlit_modal import Modal

# Function to convert image to base64
def image_to_base64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()
    
def strip_index(df):
    return pd.DataFrame(df.values, columns=df.columns)

def df_to_ascii_table(df):
    # Convert everything to strings
    df_str = df.astype(str)

    # Get column widths
    col_widths = {
        col: max(df_str[col].map(len).max(), len(col))
        for col in df_str.columns
    }

    # Build top border
    top = "+"
    for col in df_str.columns:
        top += "-" * (col_widths[col] + 2) + "+"
    top += "\n"

    # Build header row
    header = "|"
    for col in df_str.columns:
        header += " " + col.ljust(col_widths[col]) + " |"
    header += "\n"

    # Build separator under header
    mid = "+"
    for col in df_str.columns:
        mid += "-" * (col_widths[col] + 2) + "+"
    mid += "\n"

    # Build data rows
    # Build data rows
    rows = ""
    for _, row in df_str.iterrows():
        rows += "|"
        for col in df_str.columns:
            rows += " " + str(row[col]).ljust(col_widths[col]) + " |"
        rows += "\n"
        
        # Add row separator
        rows += "+"
        for col in df_str.columns:
            rows += "-" * (col_widths[col] + 2) + "+"
        rows += "\n"

    return top + header + mid + rows


def render_modal_content(img_path, message):
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        if os.path.exists(img_path):
            img = Image.open(img_path)
            st.image(img)
        else:
            st.error(f"Image not found: {img_path}")

    st.markdown("---")

    for line in message.split("\n"):
        st.markdown(line if line.strip() else "")

# Session state
if "analysis_runs" not in st.session_state:
    st.session_state.analysis_runs = []

if "modal_message" not in st.session_state:
    st.session_state.modal_message = ""

if "has_file" not in st.session_state:
    st.session_state.has_file = False

if "checkbox_key" not in st.session_state:
    st.session_state.checkbox_key = 0

if "show_invalid_modal" not in st.session_state:
    st.session_state.show_invalid_modal = False

if "show_success_modal" not in st.session_state:
    st.session_state.show_success_modal = False
    
if "active_run_id" not in st.session_state:
    st.session_state.active_run_id = None

if "saved_table" not in st.session_state:
    st.session_state.saved_table = None

if "saved_uploaded_file" not in st.session_state:
    st.session_state.saved_uploaded_file = None


# Page config
st.set_page_config(
    page_title="Statistical Analyzer",
    layout="wide",
    initial_sidebar_state="expanded"
)

with st.sidebar:
    st.header("Navigation")

    # --- Home button ---
    is_home_active = st.session_state.active_run_id is None
    if st.button(
        "Home",
        key="nav_home",
        use_container_width=True,
        type="primary" if is_home_active else "secondary"
    ):
        st.session_state.active_run_id = None
        st.rerun()

    st.markdown("---")

    # --- Analysis Runs ---
    st.subheader("Analysis Runs")

    for i, run in enumerate(st.session_state.analysis_runs):
        is_active = run["id"] == st.session_state.active_run_id

        cols = st.columns([6, 1])

        # Clickable run name (acts like a tab)
        with cols[0]:
            if st.button(
                run["name"],
                key=f"nav_run_{run['id']}",
                use_container_width=True,
                type="primary" if is_active else "secondary"
            ):
                st.session_state.active_run_id = run["id"]
                st.rerun()

        # Rename icon
        with cols[1]:
            if st.button(
                "✏️",
                key=f"rename_btn_{run['id']}",
                help="Rename run"
            ):
                st.session_state["renaming_run_id"] = run["id"]

        # Inline rename input
        if st.session_state.get("renaming_run_id") == run["id"]:
            new_name = st.text_input(
                "Rename run",
                value=run["name"],
                key=f"rename_input_{run['id']}",
                label_visibility="collapsed"
            )

            rename_cols = st.columns(2)
            with rename_cols[0]:
                if st.button("Save", key=f"save_rename_{run['id']}"):
                    run["name"] = new_name.strip() or run["name"]
                    st.session_state["renaming_run_id"] = None
                    st.rerun()

            with rename_cols[1]:
                if st.button("Cancel", key=f"cancel_rename_{run['id']}"):
                    st.session_state["renaming_run_id"] = None
                    st.rerun()



# Create modal instances
error_modal = Modal(
    "Invalid Analysis",
    key="error_modal",
)

success_modal = Modal(
    "Success!",
    key="success_modal",
)

# Styling
st.markdown("""
<style>
/* Kill the link icon that sits inside the modal title */
div[data-testid="stModal"] h3 > a {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

# Sidebar button alignment and active run emphasis
st.markdown("""
<style>

/* Target ONLY sidebar buttons - Base styling */
section[data-testid="stSidebar"] div[data-testid="stButton"] button {
    background-color: transparent !important;
    color: rgba(255, 255, 255, 0.8) !important;
    border: none !important;
    border-left: 3px solid transparent !important;
    border-radius: 6px !important;
    padding: 10px 12px !important;
    box-shadow: none !important;
    font-weight: 400 !important;
    text-align: left !important;
    transition: all 0.15s ease !important;
}

/* Secondary (inactive) buttons hover */
section[data-testid="stSidebar"] div[data-testid="stButton"] button[kind="secondary"]:hover {
    background-color: rgba(255, 255, 255, 0.05) !important;
    color: #ffffff !important;
    box-shadow: none !important;
}

/* Primary (active) buttons - Modern accent bar style */
section[data-testid="stSidebar"] div[data-testid="stButton"] button[kind="primary"] {
    background-color: rgba(228, 120, 29, 0.12) !important;
    border-left: 3px solid #e4781d !important;
    color: #ffffff !important;
    font-weight: 500 !important;
    box-shadow: none !important;
}

/* Focus — no big orange ring */
section[data-testid="stSidebar"] div[data-testid="stButton"] button:focus-visible {
    outline: none !important;
    box-shadow: none !important;
}

/* Active run — left accent only */
section[data-testid="stSidebar"] button:has(span:contains("➡️")) {
    background-color: rgba(228, 120, 29, 0.12) !important;
    color: #ffffff !important;
    border-left: 3px solid #e4781d !important;
}

/* Rename icon button — extra subtle */
section[data-testid="stSidebar"] button:has(span:contains("✏️")) {
    padding: 4px !important;
    opacity: 0.75;
}

section[data-testid="stSidebar"] button:has(span:contains("✏️")):hover {
    opacity: 1;
    background-color: rgba(255, 255, 255, 0.08) !important;
}
</style>
""", unsafe_allow_html=True)

# Modern enhancements - Glass morphism, cards, scrollbar, animations
st.markdown("""
<style>
/* Glass Morphism Sidebar */
section[data-testid="stSidebar"] {
    background: rgba(30, 30, 30, 0.8) !important;
    backdrop-filter: blur(10px) !important;
    border-right: 1px solid rgba(255, 255, 255, 0.1) !important;
}

/* Custom Modern Scrollbar */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 10px;
}

::-webkit-scrollbar-thumb {
    background: rgba(228, 120, 29, 0.5);
    border-radius: 10px;
}

::-webkit-scrollbar-thumb:hover {
    background: rgba(228, 120, 29, 0.7);
}

/* Enhanced Data Editor */
div[data-testid="stDataEditor"] {
    border-radius: 8px !important;
    overflow: hidden !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15) !important;
}

div[data-testid="stDataEditor"] table tbody tr:nth-child(even) {
    background-color: rgba(255, 255, 255, 0.02) !important;
}

div[data-testid="stDataEditor"] thead {
    background: rgba(228, 120, 29, 0.1) !important;
    font-weight: 600 !important;
}

/* Modern Typography */
h1, h2, h3 {
    font-weight: 600 !important;
    letter-spacing: -0.02em !important;
}

h2 {
    font-size: 1.5rem !important;
    margin-bottom: 1.5rem !important;
}

p, label {
    line-height: 1.6 !important;
    color: rgba(255, 255, 255, 0.87) !important;
}

/* Section Dividers with Gradient */
hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, 
        transparent 0%, 
        rgba(228, 120, 29, 0.5) 50%, 
        transparent 100%) !important;
    margin: 2rem 0 !important;
}

/* Pill-Style Tags for Selected Items */
div[data-testid="stMultiSelect"] span[data-baseweb="tag"] {
    background: rgba(228, 120, 29, 0.15) !important;
    border: 1px solid rgba(228, 120, 29, 0.3) !important;
    border-radius: 20px !important;
    padding: 4px 12px !important;
    transition: all 0.2s ease !important;
}

div[data-testid="stMultiSelect"] span[data-baseweb="tag"]:hover {
    background: rgba(228, 120, 29, 0.25) !important;
    border-color: rgba(228, 120, 29, 0.5) !important;
    transform: scale(1.05) !important;
}

/* Ambient Glow Effect for Sidebar Active Elements Only */
section[data-testid="stSidebar"] button[kind="primary"]:not(:disabled) {
    box-shadow: 0 0 20px rgba(228, 120, 29, 0.15) !important;
    animation: pulse-glow 3s ease-in-out infinite !important;
}

@keyframes pulse-glow {
    0%, 100% {
        box-shadow: 0 0 20px rgba(228, 120, 29, 0.15) !important;
    }
    50% {
        box-shadow: 0 0 30px rgba(228, 120, 29, 0.25) !important;
    }
}

/* Smooth Micro-Animations for All Interactive Elements */
button, input, select, textarea, div[data-testid="stCheckbox"], 
div[data-testid="stMultiSelect"], div[data-testid="stSelectbox"] {
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

button:active {
    transform: scale(0.98) !important;
}

/* Hover effects for all buttons */
button:hover:not(:disabled) {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
}

/* Input field animations */
div[data-testid="stMultiSelect"] div[role="combobox"]:focus-within {
    animation: input-focus 0.3s ease !important;
}

@keyframes input-focus {
    0% {
        transform: scale(1);
    }
    50% {
        transform: scale(1.01);
    }
    100% {
        transform: scale(1);
    }
}

/* Checkbox animation */
div[data-testid="stCheckbox"] input:checked + div:first-child {
    animation: checkbox-check 0.3s ease !important;
}

@keyframes checkbox-check {
    0% {
        transform: scale(0.8);
    }
    50% {
        transform: scale(1.1);
    }
    100% {
        transform: scale(1);
    }
}

/* Data editor hover effect */
div[data-testid="stDataEditor"] tbody tr {
    transition: background-color 0.2s ease !important;
}

div[data-testid="stDataEditor"] tbody tr:hover {
    background-color: rgba(228, 120, 29, 0.05) !important;
}

/* Fade in animation - only for specific elements */
@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes fadeInModal {
    from {
        opacity: 0;
        transform: scale(0.9) translateY(-20px);
    }
    to {
        opacity: 1;
        transform: scale(1) translateY(0);
    }
}

/* Apply fade in to file uploader */
div[data-testid="stFileUploader"] {
    animation: fadeIn 0.4s ease-out !important;
}

/* Apply fade in to modals - target the backdrop and content */
div[data-testid="stModal"] {
    animation: fadeInModal 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
}

div[data-testid="stModal"] * {
    animation: fadeInModal 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
}

/* Apply fade in to main data editor container (not individual rows) */
div[data-testid="stDataEditor"] {
    animation: fadeIn 0.5s ease-out !important;
}

/* Apply fade in to entire main content block when switching between homepage and runs */
.main .block-container {
    animation: fadeIn 0.6s ease-out !important;
}

/* Ensure all top-level children in main also animate */
.main .block-container > div {
    animation: fadeIn 0.6s ease-out !important;
}

/* Sidebar navigation hover animation */
section[data-testid="stSidebar"] div[data-testid="stButton"] button:hover {
    animation: button-hover 0.3s ease !important;
}

@keyframes button-hover {
    0% {
        transform: translateX(0);
    }
    50% {
        transform: translateX(3px);
    }
    100% {
        transform: translateX(0);
    }
}

/* Card-Style Containers with Depth */
div[data-testid="column"] {
    background: rgba(255, 255, 255, 0.02);
    border-radius: 12px;
    padding: 1.5rem;
    border: 1px solid rgba(255, 255, 255, 0.05);
}

/* Status Badge Styling for Subheaders */
.stSubheader {
    display: inline-block;
    padding: 8px 16px;
    background: rgba(228, 120, 29, 0.1);
    border-left: 3px solid #e4781d;
    border-radius: 4px;
    margin-bottom: 1rem !important;
}
</style>
""", unsafe_allow_html=True)


# Header and container spacing adjustments - CONSOLIDATED
st.markdown("""
<style>
/* Keep header visible for sidebar toggle but minimize it */
header[data-testid="stHeader"] {
    background-color: transparent !important;
    height: 2.5rem !important;
}

/* Hide everything in header except sidebar toggle */
header[data-testid="stHeader"] > div:not(:first-child) {
    display: none !important;
}

/* Zero top padding on all main containers */
.block-container,
div[data-testid="stMainBlockContainer"],
div[data-testid="stAppViewBlockContainer"],
section[data-testid="stAppViewContainer"] > div:first-child {
    padding-top: 0rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    margin-top: 0rem !important;
}

/* Remove spacing from vertical blocks */
div[data-testid="stVerticalBlock"],
div[data-testid="stVerticalBlockBorderWrapper"] {
    gap: 0rem !important;
    margin-top: 0rem !important;
    padding-top: 0rem !important;
}

/* Remove anchor beside modal titles */
div[data-baseweb="stMarkdownContainer"] h3 a {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

# Checkbox and column selection styling
st.markdown("""
<style>
div[data-testid="stCheckbox"] span {
    background-color: #262730 !important;
    border-radius: 4px;
    border-color: #e4781d !important;
}
</style>
""", unsafe_allow_html=True)

# Multiselect selected item styling
st.markdown("""
<style>
/* Highlight selected multiselect items with orange border like checkboxes */
div[data-baseweb="select"] > div > div > div > div {
    border: 1px solid #e4781d !important;   /* orange border */
    border-radius: 4px !important;
    box-shadow: 0 0 0 2px rgba(228, 120, 29, 0.5) !important; /* similar to checkbox hover/focus */
    background-color: transparent !important; /* keep background transparent */
    color: #ffffff !important; /* keep text readable */
}
</style>
""", unsafe_allow_html=True)

# Multiselect box styling
st.markdown("""
<style>
/* MULTISELECT — base state */
div[data-testid="stMultiSelect"] div[role="combobox"] {
    background-color: #262730 !important;
    border: 1px solid #e4781d !important;
    border-radius: 6px !important;
    box-shadow: none !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

/* Hover */
div[data-testid="stMultiSelect"] div[role="combobox"]:hover {
    border-color: #d66b1d !important;
    box-shadow: 0 0 0 2px rgba(214, 107, 29, 0.35) !important;
}

/* Focus / active / open */
div[data-testid="stMultiSelect"] div[role="combobox"][aria-expanded="true"],
div[data-testid="stMultiSelect"] div[role="combobox"]:focus,
div[data-testid="stMultiSelect"] div[role="combobox"]:focus-visible {
    outline: none !important;
    border-color: #e4781d !important;
    box-shadow: 0 0 0 3px rgba(228, 120, 29, 0.5) !important;
}

/* Remove Streamlit's red internal borders */
div[data-testid="stMultiSelect"] * {
    border-color: #e4781d !important;
}
</style>
""", unsafe_allow_html=True)

# Modal close button fix
st.markdown("""
<style>
/* Prevent close button clipping */
div[data-baseweb="modal"] header {
    padding-top: 24px !important;
    padding-right: 24px !important;
}

div[data-baseweb="modal"] button[aria-label="Close"] {
    position: relative !important;
}
</style>
""", unsafe_allow_html=True)

# Selectbox styling
st.markdown("""
<style>
/* Add spacing between file uploader and data editor */
div[data-testid="stFileUploader"] {
    margin-bottom: 1.5rem !important;
}

/* Kill Streamlit's default red outline anywhere inside the selectbox */
div[data-testid="stSelectbox"] * {
    box-shadow: none !important;
}

/* Outer container */
div[data-testid="stSelectbox"] {
    background-color: transparent !important;
}

/* BaseWeb select wrapper */
div[data-testid="stSelectbox"] div[data-baseweb="select"] {
    background-color: #262730 !important;
    border-radius: 4px !important;
}

/* The actual clickable combobox area */
div[data-testid="stSelectbox"] div[role="combobox"] {
    border: 1px solid #e4781d !important;              /* orange border */
    border-radius: 4px !important;
    padding: 2px 6px !important;
    box-shadow: 0 0 0 1px #e4781d !important;          /* orange outline */
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

/* Hover */
div[data-testid="stSelectbox"] div[role="combobox"]:hover {
    border-color: #d66b1d !important;
    box-shadow: 0 0 0 2px rgba(214, 107, 29, 0.35) !important;
}

/* Focus / open */
div[data-testid="stSelectbox"] div[role="combobox"][aria-expanded="true"],
div[data-testid="stSelectbox"] div[role="combobox"]:focus,
div[data-testid="stSelectbox"] div[role="combobox"]:focus-visible {
    outline: none !important;
    border-color: #e4781d !important;
    box-shadow: 0 0 0 3px rgba(228, 120, 29, 0.5) !important;
}

/* Arrow icon */
div[data-testid="stSelectbox"] svg {
    fill: #e4781d !important;
}

/* Style st-ep class with orange color */
.st-ep {
    background-color: #d66b1d !important;
}

</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* HARD override for the X inside multiselect pills */
div[data-testid="stMultiSelect"] span[data-baseweb="tag"] svg path {
    stroke: white !important;
    stroke-width: 2px !important;
}

/* Prevent Streamlit from recoloring it on hover/focus */
div[data-testid="stMultiSelect"] span[data-baseweb="tag"]:hover svg path,
div[data-testid="stMultiSelect"] span[data-baseweb="tag"] button:hover svg path {
    stroke: white !important;
}
</style>
""", unsafe_allow_html=True)

# Data editor checkbox styling
st.markdown("""
<style>
/* Checkbox box (unchecked) */
label[data-baseweb="checkbox"] span {
    border-color: #e4781d !important;
}

/* Checkbox SVG icon */
label[data-baseweb="checkbox"] svg {
    stroke: #e4781d !important;
    fill: none !important;
}

/* Checked state */
label[data-baseweb="checkbox"] input:checked + span svg {
    fill: #e4781d !important;
    stroke: #e4781d !important;
}

/* Hover */
label[data-baseweb="checkbox"]:hover span {
    border-color: #f08c2e !important;
}

/* Focus ring (kill red, add orange) */
label[data-baseweb="checkbox"] input:focus-visible + span {
    outline: none !important;
    box-shadow: 0 0 0 2px rgba(228, 120, 29, 0.55) !important;
}

div[data-testid="stDataEditor"] label[data-baseweb="checkbox"] span {
    border-color: #e4781d !important;
}

div[data-testid="stDataEditor"] label[data-baseweb="checkbox"] svg {
    stroke: #e4781d !important;
}

/* Disabled checkbox styling - gray out */
div[data-testid="stCheckbox"]:has(input:disabled) {
    opacity: 0.4 !important;
    cursor: not-allowed !important;
}

div[data-testid="stCheckbox"]:has(input:disabled) label {
    cursor: not-allowed !important;
}

div[data-testid="stCheckbox"]:has(input:disabled) > label > div:first-child {
    background-color: #1a1a1a !important;
    border-color: #555555 !important;
}

div[data-testid="stCheckbox"]:has(input:disabled) span {
    color: #666666 !important;
}
</style>
""", unsafe_allow_html=True)

# Checkbox box styling
st.markdown("""
<style>
/* Base checkbox styling */
div[data-testid="stCheckbox"] > label > div:first-child {
    background-color: #262730;     /* dark background */
    border: 1px solid #e4781d;     /* orange border */
    border-radius: 4px;
    width: 18px;
    height: 18px;
    transition: all 0.15s ease;
}

/* Hover effect for checkbox */
div[data-testid="stCheckbox"] > label > div:first-child:hover {
    border-color: #d66b1d;
    box-shadow: 0 0 0 2px rgba(228, 120, 29, 0.4);
}

/* Checked state styling */
div[data-testid="stCheckbox"] > label > input:checked + div:first-child {
    background-color: #e4781d;
    border-color: #e4781d;
}
</style>
""", unsafe_allow_html=True)



st.markdown("""
<style>
/* GLOBAL faded-orange button style (NON-SIDEBAR) - Targets ALL buttons in main content */
.main div[data-testid="stButton"] > button {
    background-color: rgba(228, 120, 29, 0.12) !important;
    color: rgba(255, 255, 255, 0.9) !important;
    border: 1px solid rgba(228, 120, 29, 0.3) !important;
    border-radius: 6px !important;
    font-weight: 400 !important;
    padding: 10px 16px !important;
    box-shadow: none !important;
    transition: all 0.15s ease !important;
}

/* Hover */
.main div[data-testid="stButton"] > button:hover:not(:disabled) {
    background-color: rgba(228, 120, 29, 0.2) !important;
    border-color: rgba(228, 120, 29, 0.5) !important;
    color: #ffffff !important;
}

/* Active */
.main div[data-testid="stButton"] > button:active {
    background-color: rgba(228, 120, 29, 0.25) !important;
    border-color: rgba(228, 120, 29, 0.6) !important;
}

/* Disabled */
.main div[data-testid="stButton"] > button:disabled {
    background-color: rgba(100, 100, 100, 0.1) !important;
    border-color: rgba(100, 100, 100, 0.2) !important;
    color: rgba(255, 255, 255, 0.3) !important;
    cursor: not-allowed !important;
}

/* File uploader buttons */
div[data-testid="stFileUploader"] button {
    background-color: rgba(228, 120, 29, 0.12) !important;
    color: rgba(255, 255, 255, 0.9) !important;
    border: 1px solid rgba(228, 120, 29, 0.3) !important;
    border-radius: 6px !important;
    font-weight: 400 !important;
    padding: 10px 16px !important;
    box-shadow: none !important;
    transition: all 0.15s ease !important;
}

div[data-testid="stFileUploader"] button:hover:not(:disabled) {
    background-color: rgba(228, 120, 29, 0.2) !important;
    border-color: rgba(228, 120, 29, 0.5) !important;
    color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* Force the download button container and link to match faded orange style */
div[data-testid="stDownloadButton"] {
    width: 100% !important;
    display: block !important;
}

div[data-testid="stDownloadButton"] button,
div[data-testid="stDownloadButton"] a {
    display: inline-flex !important;
    justify-content: center !important;
    align-items: center !important;
    width: 100% !important;
    min-height: 38px !important;
    padding: 10px 16px !important;
    background-color: rgba(228, 120, 29, 0.12) !important;
    color: rgba(255, 255, 255, 0.9) !important;
    border: 1px solid rgba(228, 120, 29, 0.3) !important;
    border-radius: 6px !important;
    font-weight: 400 !important;
    text-decoration: none !important;
    cursor: pointer !important;
    box-sizing: border-box !important;
    box-shadow: none !important;
    transition: all 0.15s ease !important;
}

/* Hover */
div[data-testid="stDownloadButton"] button:hover,
div[data-testid="stDownloadButton"] a:hover {
    background-color: rgba(228, 120, 29, 0.2) !important;
    border-color: rgba(228, 120, 29, 0.5) !important;
    color: #ffffff !important;
}

/* Focus */
div[data-testid="stDownloadButton"] button:focus-visible,
div[data-testid="stDownloadButton"] a:focus-visible {
    outline: none !important;
    box-shadow: 0 0 0 2px rgba(228, 120, 29, 0.4) !important;
}

/* Active */
div[data-testid="stDownloadButton"] button:active,
div[data-testid="stDownloadButton"] a:active {
    background-color: rgba(228, 120, 29, 0.25) !important;
    border-color: rgba(228, 120, 29, 0.6) !important;
}
}
</style>
""", unsafe_allow_html=True)

# Remove markdown header anchor links
st.markdown("""
<style>
/* Remove anchor link + hover icon from ALL markdown headers */
div[data-testid="stMarkdownContainer"] h1 a,
div[data-testid="stMarkdownContainer"] h2 a,
div[data-testid="stMarkdownContainer"] h3 a,
div[data-testid="stMarkdownContainer"] h4 a,
div[data-testid="stMarkdownContainer"] h5 a,
div[data-testid="stMarkdownContainer"] h6 a {
    display: none !important;
}

/* Also prevent pointer cursor / hover highlight */
div[data-testid="stMarkdownContainer"] h1,
div[data-testid="stMarkdownContainer"] h2,
div[data-testid="stMarkdownContainer"] h3,
div[data-testid="stMarkdownContainer"] h4,
div[data-testid="stMarkdownContainer"] h5,
div[data-testid="stMarkdownContainer"] h6 {
    cursor: default !important;
}
</style>
""", unsafe_allow_html=True)

# Pop Up Styling
st.markdown("""
<style>
/* ---- FINAL KILL FOR THE ARROW SCROLLBAR ---- */

/* This is the actual Streamlit content container inside the modal */
div[data-testid="stModal"] div[data-testid="stVerticalBlock"] {
    overflow: hidden !important;
}

/* Kill WebKit scrollbar + arrows inside that container */
div[data-testid="stModal"] div[data-testid="stVerticalBlock"]::-webkit-scrollbar {
    width: 0px !important;
    height: 0px !important;
}

div[data-testid="stModal"] div[data-testid="stVerticalBlock"]::-webkit-scrollbar-button {
    display: none !important;
}

/* Firefox fallback */
div[data-testid="stModal"] div[data-testid="stVerticalBlock"] {
    scrollbar-width: none !important;
}
</style>
""", unsafe_allow_html=True)

# Function to delete an analysis run
def delete_run(index):
    st.session_state.analysis_runs.pop(index)

# Main content area - Show homepage OR analysis results
if st.session_state.active_run_id:
    # Display selected analysis run
    run = next(
        (r for r in st.session_state.analysis_runs if r["id"] == st.session_state.active_run_id),
        None
    )

    if run:
        st.header(f"Analysis Results — {run['name']}", anchor=False)

        st.markdown("### Methods Applied")
        for m in run["methods"]:
            st.write("•", m)

        # Only show visualizations section if any were selected
        if run.get("visualizations") and len(run["visualizations"]) > 0:
            st.markdown("### Visualizations Applied")
            for v in run["visualizations"]:
                st.write("•", v)

        st.markdown("### Selected Cell Data")
        st.dataframe(run["data"], use_container_width=True)
        st.caption(f"Rows: {run['rows']}, Columns: {run['columns']}")

        st.markdown("---")

        btn1, btn2 = st.columns(2)

        with btn1:
            if st.button("Delete This Run"):
                st.session_state.analysis_runs = [r for r in st.session_state.analysis_runs if r["id"] != run["id"]]
                st.session_state.active_run_id = None
                st.rerun()

        with btn2:
            st.button("Save This Run")
else:
    # Show homepage with data input and configuration
    left_col, right_col = st.columns([3, 2], gap="medium")

    # Data Input
    with left_col:
        st.header("Data Input & Table", anchor=False)

        uploaded_files = st.file_uploader(
            "Upload CSV Files",
            accept_multiple_files=True,
            type="csv",
        )

        # Detect when file is closed and reset checkboxes
        if not uploaded_files and st.session_state.has_file:
            st.session_state.checkbox_key += 1
            st.session_state.has_file = False
        elif uploaded_files:
            st.session_state.has_file = True

        # Determine which table to use
        if uploaded_files:
            df = pd.read_csv(uploaded_files[-1])
            table = df.copy()
            st.session_state.saved_uploaded_file = uploaded_files[-1].name
        elif st.session_state.saved_table is not None:
            # Restore previously edited table
            table = st.session_state.saved_table.copy()
        else:
            table = pd.DataFrame(columns=["Enter your data..."])

        edited_table = st.data_editor(
            table,
            num_rows="dynamic",
            use_container_width=True,
            height=754,
            hide_index=True,
            key="main_data_editor"
        )
        edited_table.index = edited_table.index + 1
        
        # Save the edited table to session state
        st.session_state.saved_table = edited_table.copy()

        data_ready = len(edited_table.columns) > 0 and len(edited_table) > 0

    # Analysis Options
    with right_col:
        st.header("Analysis Configuration", anchor=False)

        col1 = []
        col2 = []

        if len(edited_table.columns) > 0 and len(edited_table) > 0:
            col1 = st.multiselect("Columns", edited_table.columns)
            st.session_state["current_cols"] = col1  

            # --- RESET CHECKBOXES ONLY IF USER JUST CLEARED COLUMNS ---
            if "last_cols_selected" not in st.session_state:
                st.session_state.last_cols_selected = []

            if len(st.session_state.last_cols_selected) > 0 and len(col1) == 0:
                st.session_state.checkbox_key += 1

            # Save for next interaction
            st.session_state.last_cols_selected = col1

            col2 = st.multiselect("Rows", edited_table.index)
        else:
            col1 = []
            col2 = []
            st.multiselect("Columns", [], disabled=True)
            st.multiselect("Rows", [], disabled=True)

        # Determine how many columns/rows are selected
        num_cols_selected = len(col1)
        num_rows_selected = len(col2)

        # ---- NEW: detect transition from 2+ columns → 1 column ----
        if "last_num_cols" not in st.session_state:
            st.session_state.last_num_cols = 0

        # If user DROPPED from 2+ columns to 1 column → reset dependent checkboxes
        if st.session_state.last_num_cols >= 2 and num_cols_selected == 1:
            st.session_state.checkbox_key += 1   # force re-render of checkboxes

        # Save current count for next interaction
        st.session_state.last_num_cols = num_cols_selected

        disable_two_cols = num_cols_selected < 2
        disable_one_col = num_cols_selected < 1
        disable_one_row = num_rows_selected < 1

        # Computation Options
        st.subheader("Computation Options", anchor=False)
        c1, c2 = st.columns(2)

        with c1:
            mean = st.checkbox("Mean", disabled=not data_ready or disable_one_col, key=f"mean_c1_{st.session_state.checkbox_key}")
            median = st.checkbox("Median", disabled=not data_ready or disable_one_col, key=f"median_c1_{st.session_state.checkbox_key}")
            mode = st.checkbox("Mode", disabled=not data_ready or disable_one_col, key=f"mode_c1_{st.session_state.checkbox_key}")
            variance = st.checkbox("Variance", disabled=not data_ready or disable_one_col, key=f"variance_c1_{st.session_state.checkbox_key}")
            std_dev = st.checkbox("Standard Deviation", disabled=not data_ready or disable_one_col, key=f"std_dev_c1_{st.session_state.checkbox_key}")
            percentiles = st.checkbox("Percentiles", disabled=not data_ready or disable_one_col, key=f"percentiles_c1_{st.session_state.checkbox_key}")

        with c2:
            pearson = st.checkbox("Pearson's Correlation", disabled=not data_ready or disable_two_cols, key=f"pearson_c2_{st.session_state.checkbox_key}")
            spearman = st.checkbox("Spearman's Rank", disabled=not data_ready or disable_two_cols, key=f"spearman_c2_{st.session_state.checkbox_key}")
            regression = st.checkbox("Least Squares Regression", disabled=not data_ready or disable_two_cols, key=f"regression_c2_{st.session_state.checkbox_key}")
            chi_square = st.checkbox("Chi-Square Test", disabled=not data_ready or disable_one_col, key=f"chi_square_c2_{st.session_state.checkbox_key}")
            binomial = st.checkbox("Binomial Distribution", disabled=not data_ready or disable_one_col, key=f"binomial_c2_{st.session_state.checkbox_key}")
            variation = st.checkbox("Coefficient of Variation", disabled=not data_ready or disable_one_col, key=f"variation_c2_{st.session_state.checkbox_key}")

        st.markdown("---")

        st.subheader("Visualization Options", anchor=False)
        with st.container():
            # Determine if any computation method is selected
            computation_selected = any([mean, median, mode, variance, std_dev, percentiles, pearson, spearman, regression, chi_square, binomial, variation])

            disable_viz = not computation_selected  # True if no computation is selected

            if disable_viz:
                st.session_state["viz_hist"] = False
                st.session_state["viz_box"] = False
                st.session_state["viz_scatter"] = False
                st.session_state["viz_line"] = False
                st.session_state["viz_heatmap"] = False

            # Visualization Options
            v1, v2 = st.columns(2)

            with v1:
                hist = st.checkbox(
                    "Pie Chart",
                    key="viz_hist",
                    disabled=disable_viz
                )
                box = st.checkbox(
                    "Vertical Bar Chart",
                    key="viz_box",
                    disabled=disable_viz
                )
                scatter = st.checkbox(
                    "Horizontal Bar Chart",
                    key="viz_scatter",
                    disabled=disable_viz
                )

            with v2:
                line = st.checkbox(
                    "Scatter Plot",
                    key="viz_line",
                    disabled=disable_viz
                )
                heatmap = st.checkbox(
                    "Line of Best Fit Scatter Plot",
                    key="viz_heatmap",
                    disabled=disable_viz
                )

        st.markdown("---")

        st.markdown('<div class="run-analysis-anchor">', unsafe_allow_html=True)

        # Make a copy with shifted index for row selection
        edited_table_for_loc = edited_table.copy()

        if col1 and col2:
            parsedData = edited_table_for_loc.loc[col2, col1].copy()
        elif col1:
            parsedData = edited_table_for_loc[col1].copy()
        elif col2:
            parsedData = edited_table_for_loc.loc[col2].copy()
        else:
            parsedData = edited_table_for_loc.copy()

        run_clicked = st.button(
            "Run Analysis",
            key="run_analysis",
            use_container_width=True,
            disabled=not (data_ready and computation_selected)
        )

        if run_clicked:
            non_numeric_cols = []
            numeric_required = any([
                mean, median, mode, std_dev, variance, pearson, spearman, regression, percentiles, variation,
                st.session_state.get("viz_hist", False),
                st.session_state.get("viz_box", False),
                st.session_state.get("viz_scatter", False),
                st.session_state.get("viz_line", False),
                st.session_state.get("viz_heatmap", False)
            ])

            if numeric_required:
                for col in parsedData.columns:
                    coerced = pd.to_numeric(parsedData[col], errors='coerce')
                    non_numeric_rows = parsedData[coerced.isna() & parsedData[col].notna()]
                    for row_idx, val in non_numeric_rows[col].items():
                        non_numeric_cols.append({
                            "row": row_idx,
                            "column": col,
                            "value": val
                        })

            if non_numeric_cols:
                # Prepare message
                preview = non_numeric_cols[:2]
                message = "The following non-numeric data was found:\n"
                for cell in preview:
                    message += f" - Row: {cell['row']}, Column: {cell['column']}, Value: '{cell['value']}'\n"
                if len(non_numeric_cols) > 2:
                    message += f" ...and {len(non_numeric_cols) - 2} more entries.\n"

                # Save message to session state
                st.session_state.modal_message = message

                # Open the modal immediately
                error_modal.open()

            # If all data is numeric, create the run
            else:
                run = {
                    "id": str(uuid.uuid4()),
                    "name": f"Run {len(st.session_state.analysis_runs) + 1}",
                    "table": edited_table,
                    "data": parsedData.reset_index(drop=True),
                    "columns": col1,
                    "rows": col2,
                    "methods": [
                        name for name, selected in {
                            "Mean": mean,
                            "Median": median,
                            "Mode": mode,
                            "Variance": variance,
                            "Standard Deviation": std_dev,
                            "Percentiles": percentiles,
                            "Pearson": pearson,
                            "Spearman": spearman,
                            "Regression": regression,
                            "Chi-Square": chi_square,
                            "Binomial": binomial,
                            "Variation": variation,
                        }.items() if selected
                    ],
                    "visualizations": [
                        name for name, selected in {
                            "Pie Chart": hist,
                            "Vertical Bar Chart": box,
                            "Horizontal Bar Chart": scatter,
                            "Scatter Plot": line,
                            "Line of Best Fit Scatter Plot": heatmap,
                        }.items() if selected
                    ],
                }

                st.session_state.analysis_runs.append(run)
                st.session_state.modal_message = f"Analysis '{run['name']}' has been successfully created!"
                success_modal.open()

# 🚨 FINAL OVERRIDE — Force transparent orange buttons with maximum specificity
st.markdown("""
<style>
/* Target BaseWeb buttons directly to override gray background - ALL MAIN CONTENT BUTTONS */
.main div[data-testid="stButton"] > button[data-baseweb="button"],
.main div[data-testid="stButton"] button[kind="primary"],
.main div[data-testid="stButton"] button[kind="secondary"] {
    background: linear-gradient(
        180deg,
        rgba(228, 120, 29, 0.18),
        rgba(228, 120, 29, 0.08)
    ) !important;
    background-image: linear-gradient(
        180deg,
        rgba(228, 120, 29, 0.18),
        rgba(228, 120, 29, 0.08)
    ) !important;
    color: #ffffff !important;
    border: 1px solid rgba(228, 120, 29, 0.6) !important;
    border-radius: 10px !important;
    backdrop-filter: blur(6px) !important;
    box-shadow: none !important;
}

/* Hover - ALL MAIN CONTENT BUTTONS */
.main div[data-testid="stButton"] > button[data-baseweb="button"]:hover:not(:disabled),
.main div[data-testid="stButton"] button[kind="primary"]:hover:not(:disabled),
.main div[data-testid="stButton"] button[kind="secondary"]:hover:not(:disabled) {
    background: rgba(228, 120, 29, 0.25) !important;
    box-shadow: 0 0 0 3px rgba(228, 120, 29, 0.35) !important;
}

/* Active - ALL MAIN CONTENT BUTTONS */
.main div[data-testid="stButton"] > button[data-baseweb="button"]:active,
.main div[data-testid="stButton"] button[kind="primary"]:active,
.main div[data-testid="stButton"] button[kind="secondary"]:active {
    background: rgba(228, 120, 29, 0.35) !important;
    transform: translateY(1px) !important;
}

/* Disabled - ALL MAIN CONTENT BUTTONS */
.main div[data-testid="stButton"] > button[data-baseweb="button"]:disabled,
.main div[data-testid="stButton"] button[kind="primary"]:disabled,
.main div[data-testid="stButton"] button[kind="secondary"]:disabled {
    background: rgba(100, 100, 100, 0.12) !important;
    background-image: none !important;
    border-color: rgba(100, 100, 100, 0.25) !important;
    color: rgba(255, 255, 255, 0.35) !important;
}
</style>
""", unsafe_allow_html=True)

# Render modals
if error_modal.is_open():
    with error_modal.container():
        render_modal_content(
            os.path.join(BASE_DIR, "assets", "warningSquirrel.PNG"),
            st.session_state.modal_message
        )

if success_modal.is_open():
    with success_modal.container():
        render_modal_content(
            os.path.join(BASE_DIR, "assets", "huzzahAhSquirrel.png"),
            st.session_state.modal_message
        )
