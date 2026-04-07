import threading

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    from IPython.display import display
    _DEPS_AVAILABLE = True
except ImportError:
    _DEPS_AVAILABLE = False


def _require_deps():
    if not _DEPS_AVAILABLE:
        raise ImportError(
            "plotly and ipywidgets are required. "
            "Install with: pip install plotly ipywidgets"
        )


class ProgressiveFigure:
    """
    A figure containing one or more ProgressiveAxes subplots.

    Analogous to a matplotlib Figure.  Created by pp.vis.subplots().

    After binding variables to axes, call fig.run(program, interval) to
    start progressive computation and live chart updates.
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
        """Initial placeholder figure shown before first callback tick."""
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

        fig = self._build_figure(done)
        self._display_handle.update(fig)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, program, interval=0.5):
        """
        Display the chart and start progressive computation in a background thread.
        The cell returns immediately; the single chart updates in-place.
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

        # Display placeholder once — subsequent updates replace it in-place
        self._display_handle = display(self._build_empty_figure(), display_id=True)

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
