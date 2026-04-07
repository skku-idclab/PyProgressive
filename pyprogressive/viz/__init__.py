from .chart import ProgressiveLineChart, ProgressiveScatterChart


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
