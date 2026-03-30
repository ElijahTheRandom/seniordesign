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
            Mean is used to calculate the average value of a set of numbers by summing all
            the numbers in the set and then dividing the sum by the total number of values 
            in the set. This computational method requires that all values in the set be numeric.
            \n\n An example of calculating the mean of the numbers 2, 4, and 6 would be:
            (2 + 4 + 6) / 3 = 12 / 3 = 4
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
            Median is the middle value in a set of numbers when the numbers are arranged in ascending or descending order. 
            If the set has an odd number of values, the median is the value that is exactly in the middle. 
            If the set has an even number of values, the median is calculated as the average of the two middle values.
            \n\n For example, for the set of numbers 1, 3, 3, 6, 7, 8, 9, the median is 6 because it is the middle value.This 
            computational method requires that all values in the set be numeric. 
            For the set of numbers 1, 2, 3, 4, 5, 6, 8, 9, the median would be (4 + 5) / 2 = 4.5
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
            Mode is the value that appears most frequently in a set of numbers. A set of numbers may have one mode, more than one 
            mode, or no mode at all if no number repeats. This computational method requires that all values in the set be numeric.
            \n\n For example, in the set of numbers 1, 2, 2, 3, 4, the mode is 2 because it occurs more frequently than any other number. 
            In the set 1, 1, 2, 2, 3, 3, there are multiple modes (1, 2, and 3) because each occurs with the same highest frequency.
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
            Variance is a measure of how much the values in a set of numbers differ 
            from the mean of the set. It is calculated by taking the average of the 
            squared differences between each value in the set and the mean of the set. 
            This computational method requires that all values in the set be numeric. 
            \n\n For example, for the set of numbers 2, 4, 6, the mean is 4. 
            The squared differences from the mean are (2-4)^2 = 4, (4-4)^2 = 0, and (6-4)^2 = 4. 
            The variance is the average of these squared differences: (4 + 0 + 4) / 3 = 8 / 3 ≈ 2.67
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
            Standard deviation is a measure of the amount of variation or dispersion in a set of numbers. 
            It is the square root of the variance and provides a measure of how spread out the numbers 
            in a data set are around the mean. This computational method requires that all values in the set be numeric. 
            \n\n For example, for the set of numbers 2, 4, 6, the variance is 8 / 3 ≈ 2.67, 
            so the standard deviation is √(8 / 3) ≈ 1.63
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
            Percentiles are values that divide a data set into 100 equal parts, 
            indicating the relative standing of a value within the data set. Percentiles 
            are useful for understanding the distribution of data and for comparing individual values 
            to the overall data set. For our application, they system computes percentiles for a numeric selection given user chosen percentile values. This computational method requires that all values in the set be numeric. \n\n
            for a numeric selection given user chosen percentile values. \n\n
            For example, the 25th percentile (also called the first quartile) 
            is the value below which 25% of the data fall, the 50th percentile 
            (the median) is the value below which 50% of the data fall, and 
            the 75th percentile (the third quartile) is the value below which 
            75% of the data fall.
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
            Pearson's correlation coefficient (also called Pearson's r) is a measure of the 
            linear relationship between two continuous variables. It ranges from -1 to 1, 
            where 1 indicates a perfect positive linear relationship, -1 indicates a 
            perfect negative linear relationship, and 0 indicates no linear relationship. 
            Pearson's correlation is calculated as the covariance of the two variables 
            divided by the product of their standard deviations. Our application computes
            the Pearson correlation coefficient for the two selected numeric columns of equal length. 
            \n\n For example, if we have two variables X = [1, 2, 3] and Y = [2, 4, 6], 
            the Pearson correlation coefficient would be 1, indicating a perfect positive 
            linear relationship between X and Y. This means that as X increases, Y increases 
            proportionally, and the points (X, Y) lie exactly on a straight line with a 
            positive slope.

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
            Spearman's rank correlation coefficient (also called Spearman's rho) is a nonparametric 
            measure of the monotonic relationship between two variables. Unlike Pearson's 
            correlation, which measures linear relationships, Spearman's correlation 
            assesses how well the relationship between two variables can be described 
            using a monotonic function. It is calculated by ranking the values of each 
            variable and then computing the Pearson correlation coefficient on the ranks. 
            The Spearman correlation coefficient ranges from -1 to 1, where 1 indicates 
            a perfect increasing monotonic relationship, -1 indicates a perfect decreasing 
            monotonic relationship, and 0 indicates no monotonic relationship. Our application computes the 
            Spearman rank correlation coefficient for the two selected numeric columns 
            of equal length.
            \n\n For example, if we have two variables X = [1, 2, 3] and Y = [3, 2, 1], 
            the ranks of X are [1, 2, 3] and the ranks of Y are [3, 2, 1], and the 
            Spearman correlation coefficient would be -1, indicating a perfect decreasing 
            monotonic relationship between X and Y. This means that as X increases, Y decreases 
            in a consistent manner, and the ranks of the values in X and Y move in opposite 
            directions in a perfectly monotonic decreasing fashion.

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
            Least squares regression is a method for estimating the relationship between a dependent 
            variable Y and one or more independent variables X by fitting a linear model to the 
            observed data. The method works by finding the line (or hyperplane in the case of 
            multiple predictors) that minimizes the sum of the squared differences between 
            the observed values of Y and the values predicted by the linear model. This line 
            is called the "least squares regression line," and the coefficients of the line 
            (slope and intercept in the simple linear regression case) are chosen to minimize 
            the sum of squared residuals. In simple linear regression with one predictor X, 
            the model has the form Y = b0 + b1*X + e, where b0 is the intercept, b1 is the 
            slope, and e is the error term. The least squares estimates of b0 and b1 are 
            obtained by minimizing the sum of squared residuals, and the resulting line 
            provides the best linear fit to the data in the least squares sense. Our application
            computes the least squares regression line for the two selected numeric columns, and reports
            the estimated slope and intercept of the regression line.

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
            The chi-square test is a statistical test used to determine whether there is a 
            significant association between two categorical variables. It compares the 
            observed frequencies of occurrences in each category of a contingency table 
            with the frequencies that would be expected if the variables were independent. 
            The test statistic is calculated as the sum of the squared differences between 
            observed and expected frequencies, divided by the expected frequencies. 
            The resulting chi-square statistic is then compared to a chi-square distribution 
            with the appropriate degrees of freedom to determine the p-value, which 
            indicates whether the observed association is statistically significant. 
            Our application performs the chi-square test for independence on user-selected
            categorical inputs in a valid contingency layout.
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
            The binomial distribution is a discrete probability distribution that describes the 
            number of successes in a fixed number of independent Bernoulli trials, each with 
            the same probability of success. A Bernoulli trial is an experiment with exactly 
            two possible outcomes, typically labeled "success" and "failure." The binomial 
            distribution is characterized by two parameters: n, the number of trials, and p, 
            the probability of success on each trial. The probability of observing exactly 
            k successes in n trials is given by the binomial probability mass function: 
            P(X = k) = C(n, k) * p^k * (1-p)^(n-k), where C(n, k) is the binomial 
            coefficient "n choose k." Our application allows the user to specify the (n,p) and
            requested k-range, and presents the results in tabular form.
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
            The coefficient of variation is a standardized measure of the dispersion of a probability 
            distribution or frequency distribution. It is defined as the ratio of the standard deviation 
            σ to the mean μ, often expressed as a percentage: CV = (σ / μ) * 100%. The coefficient 
            of variation allows comparison of the relative variability of datasets with different 
            units or widely different means. In our application, the Coefficient of Variation is computed for user-provided 
            numerical data, while ensuring that the mean is not zero, since the coefficient of variation 
            is undefined when the mean is zero.
            """
        )
