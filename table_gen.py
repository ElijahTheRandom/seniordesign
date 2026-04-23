import csv
import os
from collections import Counter

OUTPUT_DIR = "chart_test_data"


def ensure_output_dir() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def write_csv(filename: str, headers: list[str], rows: list[list]) -> None:
    path = os.path.join(OUTPUT_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    print(f"Wrote {path}")


def build_frequency_rows(values: list[str], value_header: str = "category") -> list[list]:
    counts = Counter(values)
    return [[k, v] for k, v in counts.items()]


def main() -> None:
    ensure_output_dir()

    # AT 3.1
    # Vertical bar chart:
    # one bar per category, heights correspond to explicit values
    vertical_bar_rows = [
        ["Apples", 12],
        ["Bananas", 7],
        ["Cherries", 15],
        ["Dates", 5],
        ["Elderberries", 10],
    ]
    write_csv(
        "at_3_1_vertical_bar.csv",
        ["category", "value"],
        vertical_bar_rows,
    )

    # Optional frequency-based vertical bar input
    vertical_bar_frequency_source = [
        ["Red"],
        ["Blue"],
        ["Red"],
        ["Green"],
        ["Blue"],
        ["Red"],
        ["Green"],
        ["Green"],
        ["Green"],
        ["Blue"],
    ]
    write_csv(
        "at_3_1_vertical_bar_frequency_source.csv",
        ["category"],
        vertical_bar_frequency_source,
    )
    write_csv(
        "at_3_1_vertical_bar_frequency_expected.csv",
        ["category", "frequency"],
        build_frequency_rows([row[0] for row in vertical_bar_frequency_source]),
    )

    # AT 3.2
    # Horizontal bar chart:
    # one bar per category, lengths correspond to explicit values
    horizontal_bar_rows = [
        ["North", 20],
        ["South", 13],
        ["East", 8],
        ["West", 17],
    ]
    write_csv(
        "at_3_2_horizontal_bar.csv",
        ["category", "value"],
        horizontal_bar_rows,
    )

    # Optional frequency-based horizontal bar input
    horizontal_bar_frequency_source = [
        ["Dog"],
        ["Cat"],
        ["Dog"],
        ["Bird"],
        ["Cat"],
        ["Dog"],
        ["Bird"],
        ["Dog"],
        ["Cat"],
    ]
    write_csv(
        "at_3_2_horizontal_bar_frequency_source.csv",
        ["category"],
        horizontal_bar_frequency_source,
    )
    write_csv(
        "at_3_2_horizontal_bar_frequency_expected.csv",
        ["category", "frequency"],
        build_frequency_rows([row[0] for row in horizontal_bar_frequency_source]),
    )

    # AT 3.3
    # Pie chart:
    # categorical/frequency data, slice proportions match frequencies
    pie_chart_rows = [
        ["A", 25],
        ["B", 15],
        ["C", 35],
        ["D", 25],
    ]
    write_csv(
        "at_3_3_pie_chart.csv",
        ["category", "frequency"],
        pie_chart_rows,
    )

    # Optional raw categorical source for pie chart
    pie_raw = (
        ["A"] * 25 +
        ["B"] * 15 +
        ["C"] * 35 +
        ["D"] * 25
    )
    write_csv(
        "at_3_3_pie_chart_raw_source.csv",
        ["category"],
        [[v] for v in pie_raw],
    )

    # AT 3.4
    # Scatter plot:
    # each row produces one point, coordinates match x/y values
    scatter_rows = [
        [1.0, 2.0],
        [2.0, 3.5],
        [3.0, 5.1],
        [4.0, 4.8],
        [5.0, 7.2],
        [6.0, 8.0],
        [7.0, 8.9],
        [8.0, 10.5],
    ]
    write_csv(
        "at_3_4_scatter_xy.csv",
        ["x", "y"],
        scatter_rows,
    )

    # AT 3.5
    # Regression overlay:
    # dataset chosen so line is exact: y = 2x + 1
    # Slope = 2.0, intercept = 1.0
    regression_rows = [
        [0, 1],
        [1, 3],
        [2, 5],
        [3, 7],
        [4, 9],
        [5, 11],
        [6, 13],
        [7, 15],
        [8, 17],
        [9, 19],
    ]
    write_csv(
        "at_3_5_regression_xy.csv",
        ["x", "y"],
        regression_rows,
    )

    regression_expected = [
        ["expected_slope", 2.0],
        ["expected_intercept", 1.0],
        ["line_equation", "y = 2x + 1"],
    ]
    write_csv(
        "at_3_5_regression_expected.csv",
        ["field", "value"],
        regression_expected,
    )

    print("\nDone.")
    print(f"All CSVs are in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()