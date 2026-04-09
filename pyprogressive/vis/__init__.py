from .axes import ProgressiveAxes
from .figure import ProgressiveFigure


def subplots(nrows=1, ncols=1, figsize=None):
    """
    Create a ProgressiveFigure with an nrows × ncols grid of subplots.

    Mirrors matplotlib's plt.subplots() API.

    Parameters
    ----------
    nrows, ncols : int
        Grid dimensions.
    figsize : (width, height) in pixels, optional
        e.g. figsize=(1200, 500).

    Returns
    -------
    (fig, ax)              when nrows=1, ncols=1
    (fig, [ax0, ax1, ...]) when nrows=1, ncols>1
    (fig, [[ax00, ...], [ax10, ...]]) otherwise

    Example::

        fig, ax = pp.vis.subplots(figsize=(800, 400))
        ax.line(mean_var, label="Mean")
        ax.set_title("Progressive Mean")
        fig.suptitle("Overall Title")
        fig.run(program, interval=0.3)
    """
    axes_grid = [
        [ProgressiveAxes(row=r + 1, col=c + 1) for c in range(ncols)]
        for r in range(nrows)
    ]
    fig = ProgressiveFigure(nrows, ncols, axes_grid, figsize=figsize)

    if nrows == 1 and ncols == 1:
        return fig, axes_grid[0][0]
    elif nrows == 1:
        return fig, axes_grid[0]
    else:
        return fig, axes_grid


class _SimpleChart:
    """
    Thin wrapper returned by pp.vis.line() / scatter() / bar().

    Internally creates a single-subplot ProgressiveFigure so all styling
    options (figsize, color, linewidth, ylim …) work identically to the
    subplots() API.
    """

    def __init__(self, fig, ax):
        self._fig = fig
        self._ax = ax

    def run(self, program, interval=0.5):
        self._fig.run(program, interval=interval)


def line(labels=None, title=None, figsize=None):
    """
    Create a single-panel progressive line chart.

    Each compiled variable becomes one line; x-axis = elapsed time.

    Parameters
    ----------
    labels  : list of str, one per compiled variable (optional)
    title   : chart / subplot title (optional)
    figsize : (width, height) in pixels (optional)

    Returns a chart object with a .run(program, interval) method.

    Example::

        chart = pp.vis.line(labels=["Mean", "Var"], title="Stats")
        chart.run(program, interval=0.3)
    """
    fig, ax = subplots(figsize=figsize)
    ax._pending_labels = labels  # resolved in run() below
    if title:
        ax.set_title(title)

    original_run = fig.run

    def _run(program, interval=0.5):
        # Bind variables to the axes now that program.args is known
        lbl_list = labels if labels is not None else [None] * len(program.args)
        for var, lbl in zip(program.args, lbl_list):
            ax.line(var, label=lbl)
        original_run(program, interval=interval)

    chart = _SimpleChart(fig, ax)
    chart.run = _run
    return chart


def scatter(x_label="X", y_label="Y", title=None, figsize=None):
    """
    Create a single-panel progressive scatter (convergence trajectory).

    Requires exactly 2 compiled variables.

    Parameters
    ----------
    x_label : axis label for the first variable
    y_label : axis label for the second variable
    title   : chart title (optional)
    figsize : (width, height) in pixels (optional)

    Returns a chart object with a .run(program, interval) method.

    Example::

        chart = pp.vis.scatter(x_label="Cov(X,Y)", y_label="Var(X)")
        chart.run(program, interval=0.3)
    """
    fig, ax = subplots(figsize=figsize)
    if title:
        ax.set_title(title)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)

    original_run = fig.run

    def _run(program, interval=0.5):
        if len(program.args) != 2:
            raise ValueError(
                f"pp.vis.scatter() requires exactly 2 variables, "
                f"got {len(program.args)}."
            )
        ax.scatter(program.args[0], program.args[1])
        original_run(program, interval=interval)

    chart = _SimpleChart(fig, ax)
    chart.run = _run
    return chart


def bar(labels=None, title=None, figsize=None):
    """
    Create a single-panel progressive bar chart.

    Each compiled variable becomes one bar series.
    GroupBy variables are rendered as grouped bars per key.

    Parameters
    ----------
    labels  : list of str, one per compiled variable (optional)
    title   : chart title (optional)
    figsize : (width, height) in pixels (optional)

    Returns a chart object with a .run(program, interval) method.

    Example::

        chart = pp.vis.bar(labels=["Group Mean"], title="By Category")
        chart.run(program, interval=0.1)
    """
    fig, ax = subplots(figsize=figsize)
    if title:
        ax.set_title(title)

    original_run = fig.run

    def _run(program, interval=0.5):
        lbl_list = labels if labels is not None else [None] * len(program.args)
        for var, lbl in zip(program.args, lbl_list):
            ax.bar(var, label=lbl)
        original_run(program, interval=interval)

    chart = _SimpleChart(fig, ax)
    chart.run = _run
    return chart
