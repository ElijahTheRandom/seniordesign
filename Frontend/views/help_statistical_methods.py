"""
views/help_statistical_methods.py
----------------------------------
Renders the PS Analytics help page for statistical methods.

WHY THIS FILE EXISTS:
    The help page provides users with information about the different
    statistical methods available in the PS Analytics application.

PUBLIC INTERFACE:
    render_help_statistical_methods()
"""

import streamlit as st

st.markdown("""
<style>
div[data-testid="stAppViewContainer"] .block-container {
    padding-left: 0.5rem !important;
    padding-right: 1rem !important;
}
</style>
""", unsafe_allow_html=True)

def render_help_statistical_methods() -> None:
    """
    Render the help page for statistical methods.
    
    Displays information about the various statistical methods
    available in the PS Analytics application.
    """
    st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        "<hr style='margin: 0; border: none; height: 1px; "
        "background: linear-gradient(90deg, transparent 0%, "
        "rgba(228, 120, 29, 0.5) 50%, transparent 100%);' />",
        unsafe_allow_html=True
    )
    
    # Create a container with padding/indentation
    content_col, _ = st.columns([3, 2], gap="medium")
    
    with content_col:
        st.header("Statistical Methods", anchor=False)

        st.markdown("""
<style>
.toc-container {
    background: linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.02) 100%);
    border: 1px solid rgba(228, 120, 29, 0.25);
    border-left: 4px solid #e4781d;
    border-radius: 12px;
    padding: 1.5rem 1.75rem;
    margin: 0.5rem 0 2rem 0;
}
.toc-label {
    font-size: 0.68rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    color: #e4781d !important;
    -webkit-text-fill-color: #e4781d !important;
    margin: 0 0 1rem 0 !important;
    background: none !important;
    background-clip: unset !important;
    -webkit-background-clip: unset !important;
    text-shadow: none !important;
}
.toc-list {
    list-style: none;
    counter-reset: toc;
    padding: 0;
    margin: 0;
}
.toc-list li {
    counter-increment: toc;
    display: flex;
    align-items: center;
    padding: 0.42rem 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
.toc-list li:last-child {
    border-bottom: none;
}
.toc-list li::before {
    content: counter(toc, decimal-leading-zero);
    font-size: 0.72rem;
    font-weight: 700;
    color: #e4781d;
    min-width: 2.4rem;
    font-variant-numeric: tabular-nums;
    opacity: 0.85;
}
.toc-list a {
    color: rgba(255, 255, 255, 0.8) !important;
    text-decoration: none !important;
    font-size: 0.92rem !important;
    font-weight: 400 !important;
    -webkit-text-fill-color: rgba(255, 255, 255, 0.8) !important;
    transition: color 0.2s, -webkit-text-fill-color 0.2s;
}
.toc-list a:hover {
    color: #e4781d !important;
    -webkit-text-fill-color: #e4781d !important;
}
</style>
<div class="toc-container">
    <p class="toc-label">Table of Contents</p>
    <ol class="toc-list">
        <li><a href="#mean">Overview of Mean</a></li>
        <li><a href="#median">Overview of Median</a></li>
        <li><a href="#mode">Overview of Mode</a></li>
        <li><a href="#variance">Overview of Variance</a></li>
        <li><a href="#standard-deviation">Overview of Standard Deviation</a></li>
        <li><a href="#percentiles">Overview of Percentiles</a></li>
        <li><a href="#pearsons-correlation">Overview of Pearson's Correlation</a></li>
        <li><a href="#spearmans-rank-correlation">Overview of Spearman's Rank Correlation</a></li>
        <li><a href="#least-squares-regression">Overview of Least Squares Regression</a></li>
        <li><a href="#chi-square-test">Overview of Chi-Square Test</a></li>
        <li><a href="#binomial-distribution">Overview of Binomial Distribution</a></li>
        <li><a href="#coefficient-of-variation">Overview of Coefficient of Variation</a></li>
    </ol>
</div>
""", unsafe_allow_html=True)

        # ------------------------------------------------------------------ #
        #  Helper: renders a consistent section divider                        #
        # ------------------------------------------------------------------ #
        def _section_divider():
            st.markdown(
                "<hr style='margin: 2.5rem 0 2rem 0; border: none; height: 1px; "
                "background: linear-gradient(90deg, rgba(228,120,29,0.4) 0%, "
                "rgba(228,120,29,0.08) 60%, transparent 100%);' />",
                unsafe_allow_html=True,
            )

        # ------------------------------------------------------------------ #
        #  1. Mean                                                             #
        # ------------------------------------------------------------------ #
        st.markdown("<div id='mean'></div>", unsafe_allow_html=True)
        st.subheader("Mean", anchor=False)
        st.markdown(
            """
            <!-- Add description here -->
            """
        )

        _section_divider()

        # ------------------------------------------------------------------ #
        #  2. Median                                                           #
        # ------------------------------------------------------------------ #
        st.markdown("<div id='median'></div>", unsafe_allow_html=True)
        st.subheader("Median", anchor=False)
        st.markdown(
            """
            <!-- Add description here -->
            """
        )

        _section_divider()

        # ------------------------------------------------------------------ #
        #  3. Mode                                                             #
        # ------------------------------------------------------------------ #
        st.markdown("<div id='mode'></div>", unsafe_allow_html=True)
        st.subheader("Mode", anchor=False)
        st.markdown(
            """
            <!-- Add description here -->
            """
        )

        _section_divider()

        # ------------------------------------------------------------------ #
        #  4. Variance                                                         #
        # ------------------------------------------------------------------ #
        st.markdown("<div id='variance'></div>", unsafe_allow_html=True)
        st.subheader("Variance", anchor=False)
        st.markdown(
            """
            <!-- Add description here -->
            """
        )

        _section_divider()

        # ------------------------------------------------------------------ #
        #  5. Standard Deviation                                               #
        # ------------------------------------------------------------------ #
        st.markdown("<div id='standard-deviation'></div>", unsafe_allow_html=True)
        st.subheader("Standard Deviation", anchor=False)
        st.markdown(
            """
            <!-- Add description here -->
            """
        )

        _section_divider()

        # ------------------------------------------------------------------ #
        #  6. Percentiles                                                      #
        # ------------------------------------------------------------------ #
        st.markdown("<div id='percentiles'></div>", unsafe_allow_html=True)
        st.subheader("Percentiles", anchor=False)
        st.markdown(
            """
            <!-- Add description here -->
            """
        )

        _section_divider()

        # ------------------------------------------------------------------ #
        #  7. Pearson's Correlation                                            #
        # ------------------------------------------------------------------ #
        st.markdown("<div id='pearsons-correlation'></div>", unsafe_allow_html=True)
        st.subheader("Pearson's Correlation", anchor=False)
        st.markdown(
            """
            <!-- Add description here -->
            """
        )

        _section_divider()

        # ------------------------------------------------------------------ #
        #  8. Spearman's Rank Correlation                                      #
        # ------------------------------------------------------------------ #
        st.markdown("<div id='spearmans-rank-correlation'></div>", unsafe_allow_html=True)
        st.subheader("Spearman's Rank Correlation", anchor=False)
        st.markdown(
            """
            <!-- Add description here -->
            """
        )

        _section_divider()

        # ------------------------------------------------------------------ #
        #  9. Least Squares Regression                                         #
        # ------------------------------------------------------------------ #
        st.markdown("<div id='least-squares-regression'></div>", unsafe_allow_html=True)
        st.subheader("Least Squares Regression", anchor=False)
        st.markdown(
            """
            <!-- Add description here -->
            """
        )

        _section_divider()

        # ------------------------------------------------------------------ #
        # 10. Chi-Square Test                                                  #
        # ------------------------------------------------------------------ #
        st.markdown("<div id='chi-square-test'></div>", unsafe_allow_html=True)
        st.subheader("Chi-Square Test", anchor=False)
        st.markdown(
            """
            <!-- Add description here -->
            """
        )

        _section_divider()

        # ------------------------------------------------------------------ #
        # 11. Binomial Distribution                                            #
        # ------------------------------------------------------------------ #
        st.markdown("<div id='binomial-distribution'></div>", unsafe_allow_html=True)
        st.subheader("Binomial Distribution", anchor=False)
        st.markdown(
            """
            <!-- Add description here -->
            """
        )

        _section_divider()

        # ------------------------------------------------------------------ #
        # 12. Coefficient of Variation                                         #
        # ------------------------------------------------------------------ #
        st.markdown("<div id='coefficient-of-variation'></div>", unsafe_allow_html=True)
        st.subheader("Coefficient of Variation", anchor=False)
        st.markdown(
            """
            <!-- Add description here -->
            """
        )
