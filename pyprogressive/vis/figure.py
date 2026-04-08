import threading

try:
    import plotly.graph_objects as go
    import plotly.io as pio
    from plotly.subplots import make_subplots
    from IPython.display import display, HTML
    _DEPS_AVAILABLE = True
except ImportError:
    _DEPS_AVAILABLE = False


def _require_deps():
    if not _DEPS_AVAILABLE:
        raise ImportError(
            "plotly and ipywidgets are required. "
            "Install with: pip install plotly ipywidgets"
        )


def _fig_to_html(fig):
    return HTML(pio.to_html(fig, full_html=False, include_plotlyjs="cdn"))


class ProgressiveFigure:
    """
    A figure containing one or more ProgressiveAxes subplots.

    Displayed as a single output that updates in-place on each callback tick.
    """

    def __init__(self, rows, cols, axes_grid):
        self._rows = rows
        self._cols = cols
        self._axes = axes_grid
        self._display_handle = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _flat_axes(self):
        return [ax for row in self._axes for ax in row]

    def _build_figure(self, done):
        flat = self._flat_axes()
        subplot_titles = [ax._title or "" for ax in flat]
        has_bar = any(ax._has_bar() for ax in flat)

        fig = make_subplots(
            rows=self._rows,
            cols=self._cols,
            subplot_titles=subplot_titles,
        )

        for ax in flat:
            for trace in ax._build_traces():
                fig.add_trace(trace, row=ax._row, col=ax._col)
            if ax._xlabel:
                fig.update_xaxes(title_text=ax._xlabel, row=ax._row, col=ax._col)
            if ax._ylabel:
                fig.update_yaxes(title_text=ax._ylabel, row=ax._row, col=ax._col)

        layout_kwargs = {}
        if has_bar:
            layout_kwargs["barmode"] = "group"
        if done:
            layout_kwargs["title_text"] = "(done)"
        if layout_kwargs:
            fig.update_layout(**layout_kwargs)

        return fig

    def _build_empty_figure(self):
        flat = self._flat_axes()
        subplot_titles = [ax._title or "" for ax in flat]
        fig = make_subplots(
            rows=self._rows,
            cols=self._cols,
            subplot_titles=subplot_titles,
        )
        for ax in flat:
            if ax._xlabel:
                fig.update_xaxes(title_text=ax._xlabel, row=ax._row, col=ax._col)
            if ax._ylabel:
                fig.update_yaxes(title_text=ax._ylabel, row=ax._row, col=ax._col)
        return fig

    def _update(self, t, done, var_index, *results):
        """Called per tick by the background thread."""
        for ax in self._flat_axes():
            ax._append(t, var_index, results)
        self._display_handle.update(_fig_to_html(self._build_figure(done)))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, program, interval=0.5):
        """
        Display one chart and start progressive computation in a background
        thread.  The chart updates in-place; only one chart is ever visible.
        """
        _require_deps()
        from ._runner import _make_callback

        var_index = {id(v): i for i, v in enumerate(program.args)}

        for ax in self._flat_axes():
            for var in ax._get_all_vars():
                if id(var) not in var_index:
                    raise ValueError(
                        f"A variable bound to subplot (row={ax._row}, col={ax._col}) "
                        f"was not found in program.args. "
                        f"Make sure you pass the same variable objects to both "
                        f"compile() and ax.line() / ax.scatter()."
                    )

        self._display_handle = display(
            _fig_to_html(self._build_empty_figure()),
            display_id=True,
        )

        n_vars = len(program.args)

        def _update_wrapper(t, done, *results):
            self._update(t, done, var_index, *results)

        callback = _make_callback(n_vars, _update_wrapper)

        thread = threading.Thread(
            target=program.run,
            kwargs={"interval": interval, "callback": callback},
            daemon=True,
        )
        thread.start()
