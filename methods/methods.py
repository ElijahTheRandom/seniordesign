from .binomial import Binomial
from .chisquared import ChiSquared
from .coefficentVariation import CoefficentVariation
from .least_squares_regression import LeastSquaresRegression
from .mean import Mean
from .median import Median
from .mode import Mode
from .pearson import PearsonCoefficient
from .percentile import Percentile
from .spearman import SpearmanCoefficient
from .standardDeviation import StandardDeviation
from .variance import Variance

methods_list = {
    "binomial": Binomial,
    "chisquared": ChiSquared,
    "coefficient_variation": CoefficentVariation,
    "least_squares_regression": LeastSquaresRegression,
    "mean": Mean,
    "median": Median,
    "mode": Mode,
    "pearson": PearsonCoefficient,
    "percentile": Percentile,
    "spearman": SpearmanCoefficient,
    "standard_deviation": StandardDeviation,
    "variance": Variance,
}