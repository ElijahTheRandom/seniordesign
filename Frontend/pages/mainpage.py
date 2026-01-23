import streamlit as st
import pandas as pd

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

# Build tabs
tab_labels = ["Main Workspace"]
tab_labels += [f"Run {i+1}" for i in range(len(st.session_state.analysis_runs))]

tabs = st.tabs(tab_labels)

# Main Workspace Tab
with tabs[0]:
    left_col, right_col = st.columns([3, 2], gap="medium")

    # Data Input
    with left_col:
        st.header("Data Input & Table")

        uploaded_files = st.file_uploader(
            "Upload CSV files",
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

        if st.button("Run Analysis", type="primary", use_container_width=True):
            run = {
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

            st.session_state.analysis_runs.append(run)
            st.rerun()

# Analysis Result Tabs
for i, tab in enumerate(tabs[1:]):
    with tab:
        run = st.session_state.analysis_runs[i]

        st.header(f"Analysis Results — Run {i+1}")
        #st.caption(f"Created: {run['timestamp']}")

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
