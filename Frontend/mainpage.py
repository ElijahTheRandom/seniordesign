import streamlit as st
import pandas as pd


# Set page configuration
st.set_page_config(
    page_title="Data Analyzer",
    layout="wide",
)

# Hide Streamlit header and adjust padding
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

# Change background color
st.markdown("""
<style>
.stApp {
 //background-color: #EEEEEE;
}
</style>
""",
unsafe_allow_html=True
)

# Set up columns for layout
top_left, top_spacer, top_right = st.columns([6, 2, 4])
left, right = st.columns([3, 2], gap="small")

# Top right buttons
with top_right:
    c1, c2, c3 = st.columns(3)
    c1.button("View Results")
    c2.button("Save Run")
    c3.button("Load Run")

with left: 
    st.header("Tabular Data Input")

    # File uploader for CSV files
    uploaded_files = st.file_uploader(
    "Upload data", accept_multiple_files=True, type="csv"
    )
    
    # Initialize with default empty table
    if uploaded_files:
        # Use the last uploaded file
        df = pd.read_csv(uploaded_files[-1])
        table = df.copy()
    else:
        # Default empty table 
        table = pd.DataFrame(columns=["Data input..."])

    # Display editable data table
    editedTable = st.data_editor(
        table,
        num_rows="dynamic",
        use_container_width=True,
        height = 450
    )

with right:
    st.header("Data Analysis Options")

    selectColmmOne = st.selectbox("Select Column 1:", options=editedTable.columns)
    selectColmnTwo = st.selectbox("Select Column 2:", options=editedTable.columns)

    st.markdown("**Select Analysis Types:**")

    cl1, cl2 = st.columns(2)

    with cl1:
        meanCheck = st.checkbox("Mean")
        medianCheck = st.checkbox("Median")
        modeCheck = st.checkbox("Mode")
        variationCheck = st.checkbox("Variation")
        stdDevCheck = st.checkbox("Standard Deviation")
        percentilesCheck = st.checkbox("Percentiles")
    with cl2:
        pearsonsCheck = st.checkbox("Pearson's Correlation")
        spearmansCheck = st.checkbox("Spearman's Rank")
        regressionCheck = st.checkbox("Least Squares Regression")
        chiSquareCheck = st.checkbox("Chi-Square Test")
        binomialCheck = st.checkbox("Binomial Distribution Test")
        varianceCheck = st.checkbox("Variance")

    st.markdown("---")
    st.header("Charts")
    st.empty()  # Placeholder for future chart implementations  


