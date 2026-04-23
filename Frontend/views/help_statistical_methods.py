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
import base64
import json
import os
import streamlit.components.v1 as components
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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
        #  Display-precision overview (referenced by every method note below) #
        # ------------------------------------------------------------------ #
        st.markdown(
            """
            #### Display precision

            Every statistic is computed in full **float64** (≈17 significant
            digits) on the backend, then rounded to **6 significant figures**
            for the on-screen stat cards so values stay readable. To see the
            full computed precision for any run, open that run's results
            page and tick **Enhanced Precision (full float64 fidelity)**
            above the stat cards. The toggle is per-run — turning it on for
            one run does not affect others.

            CSV and TSV exports always carry the full computed precision,
            regardless of the on-screen toggle. Per-method precision and
            overflow caveats (large-magnitude inputs, catastrophic
            cancellation, near-zero divisors, etc.) appear inline as warning
            notices on the results page when triggered.
            """
        )

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
            The **mean** (arithmetic average) is calculated by summing all values in a dataset
            and dividing by the total number of values. All values in the selection must be **numeric**.

            **Example:** For the set `2, 4, 6`:
            """
        )
        st.markdown("> (2 + 4 + 6) / 3 = **4**")
        st.markdown(
            "💡 Stat cards round to **6 significant figures** by default. "
            "Tick **Enhanced Precision** at the top of the run's results page "
            "to see the full ~17-digit float64 value the computation produced. "
            "CSV/TSV exports always carry the full computed precision."
        )

        _section_divider()

        # ------------------------------------------------------------------ #
        #  2. Median                                                           #
        # ------------------------------------------------------------------ #
        st.markdown("<div id='median'></div>", unsafe_allow_html=True)
        st.subheader("Median", anchor=False)
        st.markdown(
            """
            The **median** is the middle value of a dataset when values are sorted in order.

            <ul style="padding-left: 1.5rem; margin-left: 1rem;">
              <li><strong>Odd count:</strong> the median is the single middle value.</li>
              <li><strong>Even count:</strong> the median is the average of the two middle values.</li>
            </ul>

            All values in the selection must be **numeric**.

            **Examples:**
            """,
            unsafe_allow_html=True
        )
        st.markdown("> `1, 3, 3, 6, 7, 8, 9` → median = **6** (middle value)")
        st.markdown("> `1, 2, 3, 4, 5, 6, 8, 9` → median = (4 + 5) / 2 = **4.5**")
        st.markdown(
            "💡 Stat cards round to **6 significant figures** by default. "
            "Tick **Enhanced Precision** at the top of the run's results page "
            "to see the full ~17-digit float64 value the computation produced. "
            "CSV/TSV exports always carry the full computed precision."
        )

        _section_divider()

        # ------------------------------------------------------------------ #
        #  3. Mode                                                             #
        # ------------------------------------------------------------------ #
        st.markdown("<div id='mode'></div>", unsafe_allow_html=True)
        st.subheader("Mode", anchor=False)
        st.markdown(
            """
            The **mode** is the value that appears most often in a dataset. A dataset may have
            **one mode**, **multiple modes**, or **no mode** if no value repeats.
            All values in the selection must be **numeric**.

            **Tie handling:** If multiple values tie for most-frequent, the first one encountered
            in the data is returned.

            **Examples:**
            """
        )
        st.markdown("> `1, 2, 2, 3, 4` → mode = **2**")
        st.markdown("> `1, 1, 2, 2, 3, 3` → modes = **1, 2, 3** (all tie for highest frequency)")
        st.markdown(
            "💡 Stat cards round to **6 significant figures** by default. "
            "Tick **Enhanced Precision** at the top of the run's results page "
            "to see the full ~17-digit float64 value the computation produced. "
            "CSV/TSV exports always carry the full computed precision."
        )

        _section_divider()

        # ------------------------------------------------------------------ #
        #  4. Variance                                                         #
        # ------------------------------------------------------------------ #
        st.markdown("<div id='variance'></div>", unsafe_allow_html=True)
        st.subheader("Variance", anchor=False)
        st.markdown(
            """
            **Variance** measures how spread out values are relative to the mean. It is computed
            by summing the squared differences between each value and the mean, then dividing
            by **N − 1** (sample variance, a.k.a. Bessel's correction).
            All values in the selection must be **numeric**.

            **Example:** For the set `2, 4, 6` (mean = 4):
            """
        )
        st.markdown("> Squared differences: (2−4)² = 4, (4−4)² = 0, (6−4)² = 4")
        st.markdown("> Variance = (4 + 0 + 4) / (N − 1) = (4 + 0 + 4) / 2 = **4**")
        st.markdown(
            "💡 Stat cards round to **6 significant figures** by default. "
            "Tick **Enhanced Precision** at the top of the run's results page "
            "to see the full ~17-digit float64 value the computation produced. "
            "CSV/TSV exports always carry the full computed precision."
        )

        _section_divider()

        # ------------------------------------------------------------------ #
        #  5. Standard Deviation                                               #
        # ------------------------------------------------------------------ #
        st.markdown("<div id='standard-deviation'></div>", unsafe_allow_html=True)
        st.subheader("Standard Deviation", anchor=False)
        st.markdown(
            """
            **Standard deviation** measures the typical distance of values from the mean.
            It is simply the **square root of the variance**, making it easier to interpret
            because it is expressed in the same units as the original data. The same
            **sample convention** (dividing by N − 1) is used here as in variance.
            All values in the selection must be **numeric**.

            **Example:** For the set `2, 4, 6` (variance = 4):
            """
        )
        st.markdown("> Standard deviation = √4 = **2**")
        st.markdown(
            "💡 Stat cards round to **6 significant figures** by default. "
            "Tick **Enhanced Precision** at the top of the run's results page "
            "to see the full ~17-digit float64 value the computation produced. "
            "CSV/TSV exports always carry the full computed precision."
        )

        _section_divider()

        # ------------------------------------------------------------------ #
        #  6. Percentiles                                                      #
        # ------------------------------------------------------------------ #
        st.markdown("<div id='percentiles'></div>", unsafe_allow_html=True)
        st.subheader("Percentiles", anchor=False)
        st.markdown(
            """
            A **percentile** indicates the value below which a given percentage of data falls.
            Percentiles divide a dataset into 100 equal parts and are useful for understanding
            how a value compares to the rest of the distribution.

            In this application, you specify which percentile values to compute (e.g. `25, 50, 75`)
            and the results are reported for your selected numeric column.
            All values in the selection must be **numeric**.

            **How it's computed:** Percentiles use linear interpolation between adjacent data
            points. For the *p*th percentile on a sorted dataset of length *N*, the result is
            taken at position `p × (N − 1) / 100`; when that position falls between two points,
            the two nearest values are blended linearly.

            **Common percentiles:**
            """
        )
        st.markdown("> **25th percentile** (Q1) — 25% of values fall below this point")
        st.markdown("> **50th percentile** (median) — 50% of values fall below this point")
        st.markdown("> **75th percentile** (Q3) — 75% of values fall below this point")
        st.markdown(
            "💡 Stat cards round to **6 significant figures** by default. "
            "Tick **Enhanced Precision** at the top of the run's results page "
            "to see the full ~17-digit float64 value the computation produced. "
            "CSV/TSV exports always carry the full computed precision."
        )

        _section_divider()

        # ------------------------------------------------------------------ #
        #  7. Pearson's Correlation                                            #
        # ------------------------------------------------------------------ #
        st.markdown("<div id='pearsons-correlation'></div>", unsafe_allow_html=True)
        st.subheader("Pearson's Correlation", anchor=False)
        st.markdown(
            """
            **Pearson's r** measures the strength and direction of the **linear relationship**
            between two continuous variables. It ranges from **−1 to 1**:

            <ul style="padding-left: 1.5rem; margin-left: 1rem;">
              <li><strong>r = 1</strong> → perfect positive linear relationship</li>
              <li><strong>r = −1</strong> → perfect negative linear relationship</li>
              <li><strong>r = 0</strong> → no linear relationship</li>
            </ul>

            It is calculated as the covariance of the two variables divided by the product
            of their standard deviations. This application computes Pearson's r for two
            selected numeric columns of **equal length**.

            **Example:** For `X = [1, 2, 3]` and `Y = [2, 4, 6]`:
            """,
            unsafe_allow_html=True
        )
        st.markdown("> r = **1.0** — a perfect positive linear relationship (as X increases, Y increases proportionally)")
        st.markdown(
            "💡 Stat cards round to **6 significant figures** by default. "
            "Tick **Enhanced Precision** at the top of the run's results page "
            "to see the full ~17-digit float64 value the computation produced. "
            "CSV/TSV exports always carry the full computed precision."
        )
        _section_divider()

        # ------------------------------------------------------------------ #
        #  8. Spearman's Rank Correlation                                      #
        # ------------------------------------------------------------------ #
        st.markdown("<div id='spearmans-rank-correlation'></div>", unsafe_allow_html=True)
        st.subheader("Spearman's Rank Correlation", anchor=False)
        st.markdown(
            """
            **Spearman's ρ (rho)** is a **nonparametric** measure of the **monotonic relationship**
            between two variables. Unlike Pearson's r, it does not assume a linear relationship —
            it works by ranking each variable's values and then computing Pearson's r on those ranks.

            It ranges from **−1 to 1**:

            <ul style="padding-left: 1.5rem; margin-left: 1rem;">
              <li><strong>ρ = 1</strong> → perfect increasing monotonic relationship</li>
              <li><strong>ρ = −1</strong> → perfect decreasing monotonic relationship</li>
              <li><strong>ρ = 0</strong> → no monotonic relationship</li>
            </ul>

            This application computes Spearman's ρ for two selected numeric columns of **equal length**.

            **Tie handling:** Tied values receive the average of the ranks they would otherwise
            occupy (e.g., two values tied for 3rd and 4th both get rank 3.5).

            **Example:** For `X = [1, 2, 3]` and `Y = [3, 2, 1]`:
            """,
            unsafe_allow_html=True
        )
        st.markdown("> ρ = **−1.0** — as X increases, Y decreases consistently (perfect inverse monotonic relationship)")
        st.markdown(
            "💡 Stat cards round to **6 significant figures** by default. "
            "Tick **Enhanced Precision** at the top of the run's results page "
            "to see the full ~17-digit float64 value the computation produced. "
            "CSV/TSV exports always carry the full computed precision."
        )

        _section_divider()

        # ------------------------------------------------------------------ #
        #  9. Least Squares Regression                                         #
        # ------------------------------------------------------------------ #
        st.markdown("<div id='least-squares-regression'></div>", unsafe_allow_html=True)
        st.subheader("Least Squares Regression", anchor=False)
        st.markdown(
            """
            **Least squares regression** fits a straight line to observed data by finding the line
            that **minimizes the sum of squared residuals** — the squared vertical distances between
            each observed Y value and the value predicted by the line.

            For simple linear regression with one predictor, the model takes the form:
            """
        )
        st.markdown("> **Y = b₀ + b₁·X + ε**  where b₀ is the intercept, b₁ is the slope, and ε is the error term")
        st.markdown(
            """
            This application computes the regression line for two selected numeric columns
            and reports the estimated **slope** and **intercept**.
            """
        )
        st.markdown(
            "💡 Stat cards round to **6 significant figures** by default. "
            "Tick **Enhanced Precision** at the top of the run's results page "
            "to see the full ~17-digit float64 value the computation produced. "
            "CSV/TSV exports always carry the full computed precision."
        )

        _section_divider()

        # ------------------------------------------------------------------ #
        # 10. Chi-Square Test                                                  #
        # ------------------------------------------------------------------ #
        st.markdown("<div id='chi-square-test'></div>", unsafe_allow_html=True)
        st.subheader("Chi-Square Test", anchor=False)
        st.markdown(
            """
            The **chi-square test** determines whether a **statistically significant association**
            exists between two categorical variables. It works by comparing the **observed**
            frequencies in each cell of a contingency table against the **expected** frequencies
            that would arise if the variables were independent.

            The test statistic is:
            """
        )
        st.markdown("> **χ² = Σ [ (Observed − Expected)² / Expected ]**")
        st.markdown(
            """
            The resulting χ² value is compared against a chi-square distribution with the
            appropriate **degrees of freedom** to produce a **p-value**. A small p-value
            (typically < 0.05) indicates the association is statistically significant.

            This application performs the chi-square test for independence on user-selected
            categorical inputs arranged in a valid contingency layout.
            """
        )
        st.markdown(
            "💡 Stat cards round to **6 significant figures** by default. "
            "Tick **Enhanced Precision** at the top of the run's results page "
            "to see the full ~17-digit float64 value the computation produced. "
            "CSV/TSV exports always carry the full computed precision."
        )

        _section_divider()

        # ------------------------------------------------------------------ #
        # 11. Binomial Distribution                                            #
        # ------------------------------------------------------------------ #
        st.markdown("<div id='binomial-distribution'></div>", unsafe_allow_html=True)
        st.subheader("Binomial Distribution", anchor=False)
        st.markdown(
            """
            The **binomial distribution** models the number of **successes** in a fixed number
            of independent **Bernoulli trials** — experiments with exactly two outcomes
            ("success" or "failure"), each sharing the same probability of success.

            It is defined by two parameters:

            <ul style="padding-left: 1.5rem; margin-left: 1rem;">
              <li><strong>n</strong> — total number of trials</li>
              <li><strong>p</strong> — probability of success on each trial</li>
            </ul>

            The probability of exactly **k** successes is given by the **probability mass function**:
            """,
            unsafe_allow_html=True
        )
        st.markdown("> **P(X = k) = C(n, k) · pᵏ · (1−p)ⁿ⁻ᵏ**  where C(n, k) is \"n choose k\"")
        st.markdown(
            """
            This application lets you specify **n**, **p**, and a **k-range**, then presents
            the PMF, CDF, and survival function for each k in that range in tabular form.
            """
        )
        st.markdown(
            "💡 Stat cards round to **6 significant figures** by default. "
            "Tick **Enhanced Precision** at the top of the run's results page "
            "to see the full ~17-digit float64 value the computation produced. "
            "CSV/TSV exports always carry the full computed precision."
        )

        _section_divider()

        # ------------------------------------------------------------------ #
        # 12. Coefficient of Variation                                         #
        # ------------------------------------------------------------------ #
        st.markdown("<div id='coefficient-of-variation'></div>", unsafe_allow_html=True)
        st.subheader("Coefficient of Variation", anchor=False)
        st.markdown(
            """
            The **coefficient of variation (CV)** is a standardized measure of dispersion that
            expresses variability **relative to the mean**. Because it is unit-free, it allows
            meaningful comparisons between datasets with different units or scales.

            It is defined as:
            """
        )
        st.markdown("> **CV = (σ / μ) × 100%**  where σ is the standard deviation and μ is the mean")
        st.markdown(
            """
            ⚠ CV is **undefined when the mean is zero**. This application will flag that condition
            and skip the computation if the mean of the selected data is zero.
            """
        )
        st.markdown(
            "💡 Stat cards round to **6 significant figures** by default. "
            "Tick **Enhanced Precision** at the top of the run's results page "
            "to see the full ~17-digit float64 value the computation produced. "
            "CSV/TSV exports always carry the full computed precision."
        )
