from .chart import ProgressiveLineChart, ProgressiveScatterChart
from .axes import ProgressiveAxes
from .figure import ProgressiveFigure


def subplots(nrows=1, ncols=1):
    """
    Create a ProgressiveFigure with an nrows × ncols grid of subplots.

    Mirrors matplotlib's plt.subplots() API.

    Returns
    -------
    (fig, ax)              when nrows=1, ncols=1  — single ProgressiveAxes
    (fig, [ax0, ax1, ...]) when nrows=1, ncols>1  — flat list
    (fig, [[ax00, ...], [ax10, ...]]) otherwise   — list of lists

    Example::

        fig, ax = pp.viz.subplots()
        ax.line(mean_var, label="Mean")
        ax.set_title("Progressive Mean")
        fig.run(program, interval=0.3)

        fig, (ax1, ax2) = pp.viz.subplots(1, 2)
        ax1.line(cov_var, label="Covariance")
        ax2.scatter(cov_var, var_var)
        fig.run(program, interval=0.3)
    """
    # Build 2-D grid of ProgressiveAxes (1-based row/col for Plotly)
    axes_grid = [
        [ProgressiveAxes(row=r + 1, col=c + 1) for c in range(ncols)]
        for r in range(nrows)
    ]
    fig = ProgressiveFigure(nrows, ncols, axes_grid)

    # Return axes in matplotlib-compatible shape
    if nrows == 1 and ncols == 1:
        return fig, axes_grid[0][0]
    elif nrows == 1:
        return fig, axes_grid[0]          # flat list
    else:
        return fig, axes_grid             # list of lists


def line(labels=None, title="Progressive Chart"):
    """
    Create a progressive line chart.

    Each compiled variable becomes one line on the chart.
    x-axis = elapsed computation time, y-axis = current value.

    Args:
        labels: list of str, one per compiled variable (optional)
        title:  chart title

    Returns:
        ProgressiveLineChart

    Example::

        chart = pp.viz.line(labels=["Cov(X,Y)", "Var(X)", "Var(Y)"])
        chart.run(program, interval=0.3)
    """
    return ProgressiveLineChart(labels=labels, title=title)


def scatter(x_label="X", y_label="Y", title="Progressive Scatter"):
    """
    Create a progressive scatter chart for exactly 2 variables.

    Shows the convergence trajectory as the two estimates drift toward
    their final values.

    Args:
        x_label: axis label for the first variable
        y_label: axis label for the second variable
        title:   chart title

    Returns:
        ProgressiveScatterChart

    Example::

        chart = pp.viz.scatter(x_label="Cov(X,Y)", y_label="Var(X)")
        chart.run(program, interval=0.3)
    """
    return ProgressiveScatterChart(x_label=x_label, y_label=y_label, title=title)
