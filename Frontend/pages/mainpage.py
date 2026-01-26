import streamlit as st
import pandas as pd
import uuid

# Session state
if "analysis_runs" not in st.session_state:
    st.session_state.analysis_runs = []

# Page config
st.set_page_config(
    page_title="Statistical Analyzer",
    layout="wide",
)

# Styling
st.markdown("""
<style>
header[data-testid="stHeader"] { display: none; }
.block-container {
    padding-top: 0rem !important;
    padding-left: 1rem;
    padding-right: 1rem;
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

st.markdown("""
<style>
div[data-testid="stSelectbox"] > div {
    background-color: #262730 !important;
    border: 1px solid #e4781d !important;
    border-radius: 6px !important;
}

div[data-testid="stSelectbox"] > div:hover {
    border-color: #d66b1d !important;
}

div[data-testid="stSelectbox"] > div:has(input:focus) {
    border-color: #e4781d !important;
    box-shadow: 0 0 0 1px #e4781d !important;
}

div[data-testid="stSelectbox"] svg {
    fill: #e4781d !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
div[data-testid="stCheckbox"] > label > div:first-child {
    background-color: #262730;     /* dark background */
    border: 1px solid #e4781d;     /* orange border */
    border-radius: 4px;
    width: 18px;
    height: 18px;
    transition: all 0.15s ease;
}

div[data-testid="stCheckbox"] > label > div:first-child:hover {
    border-color: #d66b1d;
    box-shadow: 0 0 0 2px rgba(228, 120, 29, 0.4);
}

div[data-testid="stCheckbox"] > label > input:checked + div:first-child {
    background-color: #e4781d;
    border-color: #e4781d;
}
</style>
""", unsafe_allow_html=True)

# Button styling
st.markdown("""
<style>
div[data-testid="stButton"] button,
div[data-testid="stFileUploader"] button {
    background-color: #262730 !important;   /* dark background */
    color: white !important;                /* text color */
    border: 1px solid #e4781d !important;  /* orange border */
    border-radius: 6px !important;
    font-weight: 600;
    padding: 6px 16px;
    transition: all 0.15s ease;
    cursor: pointer;
}

div[data-testid="stButton"] button:hover,
div[data-testid="stFileUploader"] button:hover {
    border-color: #d66b1d !important;
    box-shadow: 0 0 0 2px rgba(228, 120, 29, 0.4);
    background-color: #2d2d38 !important; /* slightly lighter on hover */
}

div[data-testid="stButton"] button:active,
div[data-testid="stFileUploader"] button:active {
    background-color: #1f1f29 !important;
    border-color: #e4781d !important;
}
</style>
""", unsafe_allow_html=True)

def delete_run(index):
    st.session_state.analysis_runs.pop(index)

# Build tabs
tab_labels = ["Main Workspace"]
tab_labels += [run["name"] for run in st.session_state.analysis_runs]

tabs = st.tabs(tab_labels)

st.markdown("""
<style>
div[data-testid="stTabs"] button[role="tab"] {
    color: #e4781d !important;
    font-weight: 600 !important;
    background: transparent !important;
}

div[data-testid="stTabs"] button[role="tab"]:hover {
    color: #d66b1d !important;
}

div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color: #e4781d !important;
}

div[data-testid="stTabs"] div[role="tablist"] > div:last-child {
    background-color: #d66b1d !important;
    height: 3px !important;
    border-radius: 2px !important;
}
</style>
""", unsafe_allow_html=True)


# Main Workspace Tab
with tabs[0]:
    left_col, right_col = st.columns([3, 2], gap="medium")

    # Data Input
    with left_col:
        st.header("Data Input & Table")

        uploaded_files = st.file_uploader(
            "Upload CSV Files",
            accept_multiple_files=True,
            type="csv",
        )

        if uploaded_files:
            df = pd.read_csv(uploaded_files[-1])
            table = df.copy()
            st.info(f"Loaded: {uploaded_files[-1].name}")
        else:
            table = pd.DataFrame(columns=["Enter your data..."])

        edited_table = st.data_editor(
            table,
            num_rows="dynamic",
            use_container_width=True,
            height=450,
        )

    # Analysis Options
    with right_col:
        st.header("Analysis Configuration")

        col1 = st.selectbox("Primary Column", edited_table.columns)
        col2 = st.selectbox("Secondary Column", edited_table.columns)

        st.subheader("Analysis Types")

        c1, c2 = st.columns(2)

        with c1:
            mean = st.checkbox("Mean")
            median = st.checkbox("Median")
            mode = st.checkbox("Mode")
            variance = st.checkbox("Variance")
            std_dev = st.checkbox("Standard Deviation")
            percentiles = st.checkbox("Percentiles")

        with c2:
            pearson = st.checkbox("Pearson's Correlation")
            spearman = st.checkbox("Spearman's Rank")
            regression = st.checkbox("Least Squares Regression")
            chi_square = st.checkbox("Chi-Square Test")
            binomial = st.checkbox("Binomial Distribution")
            variation = st.checkbox("Coefficient of Variation")

        st.markdown("---")

        st.markdown('<div class="run-analysis-anchor">', unsafe_allow_html=True)

        run_clicked = st.button(
            "Run Analysis",
            key="run_analysis",
            use_container_width=True
        )

        if run_clicked:
            run = {
                "id": str(uuid.uuid4()),
                "name": f"Run {len(st.session_state.analysis_runs) + 1}",
                "table": edited_table,
                "col1": col1,
                "col2": col2,
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
            }


            st.markdown('</div>', unsafe_allow_html=True)

            st.session_state.analysis_runs.append(run)
            st.rerun()

# Analysis Result Tabs
for i, tab in enumerate(tabs[1:]):
    with tab:
        run = st.session_state.analysis_runs[i]

        st.header(f"Analysis Results — {run['name']}")

        st.markdown("### Columns Used")
        st.write(run["col1"], "vs", run["col2"])

        st.markdown("### Methods Applied")
        for m in run["methods"]:
            st.write("•", m)

        st.markdown("### Data Snapshot")
        st.dataframe(run["table"], use_container_width=True)

        st.markdown("---")

        if st.button("Delete This Run", key=f"delete_{i}"):
            st.session_state.analysis_runs.pop(i)
            st.rerun()
