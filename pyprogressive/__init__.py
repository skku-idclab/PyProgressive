from .array import array, reset
from .variable import Variable
from .midlevel import Program, compile, each, accum, group, G
from . import vis


def sqrt(x):
    """Square root of a progressive expression.  Equivalent to x ** 0.5.

    Use this to build derived variables such as Pearson correlation:

        corr = cov_xy / sqrt(var_x * var_y)
        program = pp.compile(cov_xy, var_x, var_y, corr)
        ax.line(corr, label="Correlation")
    """
    return x ** 0.5
