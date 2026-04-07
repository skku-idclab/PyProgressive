import threading

try:
    import plotly.graph_objects as go
    import ipywidgets as widgets
    from IPython.display import display, clear_output
    _PLOTLY_AVAILABLE = True
except ImportError:
    _PLOTLY_AVAILABLE = False


def _require_deps():
    if not _PLOTLY_AVAILABLE:
        raise ImportError(
            "plotly and ipywidgets are required. "
            "Install with: pip install plotly ipywidgets"
        )


class ProgressiveLineChart:
    """
    Progressive line chart: x = elapsed time, each variable is one line.

    Computation runs in a background thread so the cell returns immediately
    and Jupyter can render each update in real-time.

    Usage::

        chart = ProgressiveLineChart(labels=["mean", "var"], title="My Stats")
        chart.run(program, interval=0.5)
    """

    def __init__(self, labels=None, title="Progressive Chart"):
        self.labels = labels
        self.title = title
        self._history_t = []
        self._history_v = []
        self._n_vars = None
        self._output = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_figure(self, done):
        labels = self.labels if self.labels is not None else [
            f"var{i}" for i in range(self._n_vars)
        ]
        title_text = f"{self.title}  (done)" if done else self.title
        traces = [
            go.Scatter(
                x=list(self._history_t),
                y=list(self._history_v[i]),
                mode="lines",
                name=labels[i],
            )
            for i in range(self._n_vars)
            if self._history_v[i] and self._history_v[i][-1] is not None
        ]
        return go.Figure(
            data=traces,
            layout=go.Layout(
                title=dict(text=title_text),
                xaxis=dict(title="Elapsed Time (s)"),
                yaxis=dict(title="Value"),
            ),
        )

    def _update(self, t, done, *values):
        """Called by ProgressiveRunner on every callback tick (background thread)."""
        scalar_values = []
        for v in values:
            if isinstance(v, dict):
                if not hasattr(self, "_warned_group"):
                    self._warned_group = True
                    print(
                        "Warning: GroupBy variable detected — "
                        "ProgressiveLineChart only plots scalar variables."
                    )
                scalar_values.append(None)
            else:
                scalar_values.append(float(v))

        self._history_t.append(t)
        for i, v in enumerate(scalar_values):
            self._history_v[i].append(v)

        fig = self._build_figure(done)
        with self._output:
            clear_output(wait=True)
            display(fig)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, program, interval=0.5):
        """
        Display the chart and start computation in a background thread.
        The cell returns immediately; updates appear in real-time.
        The chart title changes to '(done)' when computation is complete.
        """
        _require_deps()
        from ._runner import ProgressiveRunner

        self._n_vars = len(program.args)
        self._history_t = []
        self._history_v = [[] for _ in range(self._n_vars)]
        self._output = widgets.Output()
        display(self._output)

        def _run():
            ProgressiveRunner(program, self).run(interval)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()


class ProgressiveScatterChart:
    """
    Progressive scatter chart for exactly 2 variables.

    Shows the convergence trajectory: as more data is processed the point
    (var0, var1) drifts toward its final value. The trajectory is drawn as
    a faint line; the current position is highlighted as a marker.

    Computation runs in a background thread so the cell returns immediately
    and Jupyter can render each update in real-time.

    Usage::

        chart = ProgressiveScatterChart(x_label="Cov(X,Y)", y_label="Var(X)")
        chart.run(program, interval=0.5)
    """

    def __init__(self, x_label="X", y_label="Y", title="Progressive Scatter"):
        self.x_label = x_label
        self.y_label = y_label
        self.title = title
        self._history_x = []
        self._history_y = []
        self._output = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_figure(self, done):
        title_text = f"{self.title}  (done)" if done else self.title
        return go.Figure(
            data=[
                go.Scatter(
                    x=list(self._history_x),
                    y=list(self._history_y),
                    mode="lines",
                    name="trajectory",
                    line=dict(color="lightblue", width=1.5),
                ),
                go.Scatter(
                    x=[self._history_x[-1]],
                    y=[self._history_y[-1]],
                    mode="markers",
                    name="current",
                    marker=dict(color="crimson", size=10),
                ),
            ],
            layout=go.Layout(
                title=dict(text=title_text),
                xaxis=dict(title=self.x_label),
                yaxis=dict(title=self.y_label),
            ),
        )

    def _update(self, t, done, x_val, y_val):
        """Called by ProgressiveRunner on every callback tick (background thread)."""
        self._history_x.append(float(x_val))
        self._history_y.append(float(y_val))

        fig = self._build_figure(done)
        with self._output:
            clear_output(wait=True)
            display(fig)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, program, interval=0.5):
        """
        Display the chart and start computation in a background thread.
        The cell returns immediately; updates appear in real-time.
        The chart title changes to '(done)' when computation is complete.
        """
        _require_deps()
        from ._runner import ProgressiveRunner

        if len(program.args) != 2:
            raise ValueError(
                f"ProgressiveScatterChart requires exactly 2 variables, "
                f"got {len(program.args)}."
            )
        self._history_x = []
        self._history_y = []
        self._output = widgets.Output()
        display(self._output)

        def _run():
            ProgressiveRunner(program, self).run(interval)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
