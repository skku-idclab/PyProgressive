import threading

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import ipywidgets as widgets
    from IPython.display import display, clear_output
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

    Analogous to a matplotlib Figure.  Created by pp.viz.subplots().

    After binding variables to axes, call fig.run(program, interval) to
    start progressive computation and live chart updates.
    """

    def __init__(self, rows, cols, axes_grid):
        """
        Args:
            rows, cols:  subplot grid dimensions
            axes_grid:   List[List[ProgressiveAxes]]  (2-D, row-major)
        """
        self._rows = rows
        self._cols = cols
        self._axes = axes_grid   # _axes[r][c]
        self._output = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _flat_axes(self):
        """Return all axes in row-major order."""
        return [ax for row in self._axes for ax in row]

    def _build_figure(self, done):
        flat = self._flat_axes()

        # subplot_titles: one entry per cell (empty string = no title)
        subplot_titles = [ax._title or "" for ax in flat]

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

        if done:
            fig.update_layout(title_text="(done)")

        return fig

    def _update(self, t, done, var_index, *results):
        """Called per tick by the background thread."""
        for ax in self._flat_axes():
            ax._append(t, var_index, results)

        fig = self._build_figure(done)
        with self._output:
            clear_output(wait=True)
            display(fig)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, program, interval=0.5):
        """
        Start progressive computation and live chart updates.

        Args:
            program:  pp.compile(...) result
            interval: minimum seconds of computation between chart updates
        """
        _require_deps()
        from ._runner import _make_callback

        # Build variable → result-index map
        var_index = {id(v): i for i, v in enumerate(program.args)}

        # Validate: every bound variable must be in program.args
        for ax in self._flat_axes():
            for var in ax._get_all_vars():
                if id(var) not in var_index:
                    raise ValueError(
                        f"A variable bound to subplot (row={ax._row}, col={ax._col}) "
                        f"was not found in program.args. "
                        f"Make sure you pass the same variable objects to both "
                        f"compile() and ax.line() / ax.scatter()."
                    )

        self._output = widgets.Output()
        display(self._output)

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
