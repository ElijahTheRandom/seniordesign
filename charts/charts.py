from .bestFit import BestFit
from .horBar import HorBar
from .pieChart import PieChart
from .scatPlot import ScatPlot
from .vertBar import VertBar
from methods.binomial import Binomial

charts_list = {
    "binomial": Binomial,
    "best_fit": BestFit,
    "hor_bar": HorBar,
    "pie_chart": PieChart,
    "scat_plot": ScatPlot,
    "vert_bar": VertBar,
}