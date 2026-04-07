import threading

try:
    import plotly.graph_objects as go
    from IPython.display import display
    _PLOTLY_AVAILABLE = True
except ImportError:
    _PLOTLY_AVAILABLE = False


def _require_deps():
    if not _PLOTLY_AVAILABLE:
        raise ImportError(
            "plotly is required. Install with: pip install plotly"
        )


class ProgressiveLineChart:
    """
    Progressive line chart: x = elapsed time, each variable is one line.

    The chart is displayed once and updated in-place on each callback tick.
    """

    def __init__(self, labels=None, title="Progressive Chart"):
        self.labels = labels
        self.title = title
        self._history_t = []
        self._history_v = []
        self._n_vars = None
        self._display_handle = None

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

    def _build_empty_figure(self):
        labels = self.labels if self.labels is not None else [
            f"var{i}" for i in range(self._n_vars)
        ]
        return go.Figure(
            data=[go.Scatter(x=[], y=[], mode="lines", name=lbl) for lbl in labels],
            layout=go.Layout(
                title=dict(text=self.title),
                xaxis=dict(title="Elapsed Time (s)"),
                yaxis=dict(title="Value"),
            ),
        )

    def _update(self, t, done, *values):
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

        self._display_handle.update(self._build_figure(done))

    def run(self, program, interval=0.5):
        _require_deps()
        from ._runner import ProgressiveRunner

        self._n_vars = len(program.args)
        self._history_t = []
        self._history_v = [[] for _ in range(self._n_vars)]
        self._display_handle = display(self._build_empty_figure(), display_id=True)

        thread = threading.Thread(
            target=lambda: ProgressiveRunner(program, self).run(interval),
            daemon=True,
        )
        thread.start()


class ProgressiveScatterChart:
    """
    Progressive scatter chart for exactly 2 variables.

    Shows the convergence trajectory as the two estimates drift toward
    their final values. The chart is displayed once and updated in-place.
    """

    def __init__(self, x_label="X", y_label="Y", title="Progressive Scatter"):
        self.x_label = x_label
        self.y_label = y_label
        self.title = title
        self._history_x = []
        self._history_y = []
        self._display_handle = None

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

    def _build_empty_figure(self):
        return go.Figure(
            data=[
                go.Scatter(x=[], y=[], mode="lines", name="trajectory",
                           line=dict(color="lightblue", width=1.5)),
                go.Scatter(x=[], y=[], mode="markers", name="current",
                           marker=dict(color="crimson", size=10)),
            ],
            layout=go.Layout(
                title=dict(text=self.title),
                xaxis=dict(title=self.x_label),
                yaxis=dict(title=self.y_label),
            ),
        )

    def _update(self, t, done, x_val, y_val):
        self._history_x.append(float(x_val))
        self._history_y.append(float(y_val))
        self._display_handle.update(self._build_figure(done))

    def run(self, program, interval=0.5):
        _require_deps()
        from ._runner import ProgressiveRunner

        if len(program.args) != 2:
            raise ValueError(
                f"ProgressiveScatterChart requires exactly 2 variables, "
                f"got {len(program.args)}."
            )
        self._history_x = []
        self._history_y = []
        self._display_handle = display(self._build_empty_figure(), display_id=True)

        thread = threading.Thread(
            target=lambda: ProgressiveRunner(program, self).run(interval),
            daemon=True,
        )
        thread.start()
