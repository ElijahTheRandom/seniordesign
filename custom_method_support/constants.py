"""Constants shared across custom method support modules."""

BUNDLE_SCHEMA_VERSION = 1

BUILTIN_TOOL_INFO: dict[str, dict[str, str]] = {
    "mean": {
        "display_name": "Mean",
        "description": "Average value of a single numeric column.",
        "input_type": "one_column",
        "source": "standard",
    },
    "median": {
        "display_name": "Median",
        "description": "Middle value of a single numeric column.",
        "input_type": "one_column",
        "source": "standard",
    },
    "mode": {
        "display_name": "Mode",
        "description": "Most frequent value in a single numeric column.",
        "input_type": "one_column",
        "source": "standard",
    },
    "variance": {
        "display_name": "Variance",
        "description": "Variance of a single numeric column.",
        "input_type": "one_column",
        "source": "standard",
    },
    "standard_deviation": {
        "display_name": "Standard Deviation",
        "description": "Standard deviation of a single numeric column.",
        "input_type": "one_column",
        "source": "standard",
    },
    "percentile": {
        "display_name": "Percentile",
        "description": "Percentile calculation for a single numeric column.",
        "input_type": "one_column",
        "source": "standard",
    },
    "coefficient_variation": {
        "display_name": "Coefficient of Variation",
        "description": "Relative spread of a single numeric column.",
        "input_type": "one_column",
        "source": "standard",
    },
    "pearson": {
        "display_name": "Pearson's Correlation",
        "description": "Pearson correlation between two numeric columns.",
        "input_type": "two_column",
        "source": "standard",
    },
    "spearman": {
        "display_name": "Spearman's Rank",
        "description": "Spearman rank correlation between two numeric columns.",
        "input_type": "two_column",
        "source": "standard",
    },
    "least_squares_regression": {
        "display_name": "Least Squares Regression",
        "description": "Best-fit line and regression details for two numeric columns.",
        "input_type": "two_column",
        "source": "standard",
    },
    "chisquared": {
        "display_name": "Chi-Square Test",
        "description": "Chi-square test using two columns of categorical or grouped data.",
        "input_type": "two_column",
        "source": "standard",
    },
}
