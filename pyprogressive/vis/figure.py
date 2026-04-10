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


def _extract_gtoken_index(node):
    """
    Walk an expression tree (before BQ conversion) and return the tuple
    access index of the first DataItemToken whose id is "GToken", or None.
    """
    from ..expression import BinaryOperationNode, PowerN
    from ..token import DataItemToken
    from ..variable import Variable

    if node is None:
        return None
    if isinstance(node, DataItemToken) and node.id == "GToken":
        return node.index
    if isinstance(node, Variable):
        return _extract_gtoken_index(node.expr)
    if isinstance(node, BinaryOperationNode):
        result = _extract_gtoken_index(node.left)
        if result is not None:
            return result
        return _extract_gtoken_index(node.right)
    if isinstance(node, PowerN):
        result = _extract_gtoken_index(node.base)
        if result is not None:
            return result
        return _extract_gtoken_index(node.exponent)
    # generic fallback
    for attr in ("expr",):
        child = getattr(node, attr, None)
        if child is not None:
            result = _extract_gtoken_index(child)
            if result is not None:
                return result
    return None


class ProgressiveFigure:
    """
    A figure containing one or more ProgressiveAxes subplots.

    Displayed as a single output that updates in-place on each callback tick.
    """

    def __init__(self, rows, cols, axes_grid, figsize=None):
        self._rows = rows
        self._cols = cols
        self._axes = axes_grid
        self._figsize = figsize
        self._suptitle = None
        self._display_handle = None
        self._progress = 0.0   # 0.0 ~ 1.0
        self._elapsed_t = 0.0  # elapsed seconds

    # ------------------------------------------------------------------
    # Public configuration API
    # ------------------------------------------------------------------

    def suptitle(self, text):
        """Set an overall title for the entire figure (above all subplots)."""
        self._suptitle = text

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _flat_axes(self):
        return [ax for row in self._axes for ax in row]

    def _build_specs(self):
        """Return subplot specs for make_subplots.

        Pie axes need {"type": "pie"}; everything else uses the default {"type": "xy"}.
        """
        return [
            [
                {"type": "pie"} if self._axes[r][c]._has_pie() else {"type": "xy"}
                for c in range(self._cols)
            ]
            for r in range(self._rows)
        ]

    def _collect_shapes(self):
        """Gather axhline / axvline shapes from every non-pie subplot axes."""
        shapes = []
        flat = self._flat_axes()
        for i, ax in enumerate(flat):
            if ax._has_pie():
                continue  # pie subplots have no xy axes — skip
            subplot_idx = i + 1
            xref = "x" if subplot_idx == 1 else f"x{subplot_idx}"
            yref = "y" if subplot_idx == 1 else f"y{subplot_idx}"
            shapes.extend(ax._get_shapes(xref, yref))
        return shapes

    def _apply_layout(self, fig, done):
        flat = self._flat_axes()
        has_bar = any(ax._has_bar() for ax in flat)

        layout_kwargs = {}
        if has_bar:
            layout_kwargs["barmode"] = "group"

        BAR_WIDTH = 20
        filled = BAR_WIDTH if done else int(self._progress * BAR_WIDTH)
        bar = "█" * filled + "░" * (BAR_WIDTH - filled)
        pct_int = 100 if done else int(self._progress * 100)
        suffix = f"[{bar}] {pct_int}% | {self._elapsed_t:.1f}s"
        if done:
            suffix += " ✓"

        title_text = self._suptitle or ""
        if title_text:
            title_text = f"{title_text} — {suffix}"
        else:
            title_text = suffix
        layout_kwargs["title_text"] = title_text

        if self._figsize is not None:
            layout_kwargs["width"] = self._figsize[0]
            layout_kwargs["height"] = self._figsize[1]

        if layout_kwargs:
            fig.update_layout(**layout_kwargs)

        for ax in flat:
            if ax._has_pie():
                continue  # no y-axis on pie subplots
            if ax._ylim is not None:
                fig.update_yaxes(range=list(ax._ylim), row=ax._row, col=ax._col)

        return fig

    def _build_figure(self, done):
        flat = self._flat_axes()
        subplot_titles = [ax._title or "" for ax in flat]

        fig = make_subplots(
            rows=self._rows,
            cols=self._cols,
            subplot_titles=subplot_titles,
            specs=self._build_specs(),
        )
        for ax in flat:
            for trace in ax._build_traces():
                fig.add_trace(trace, row=ax._row, col=ax._col)
            if ax._has_pie():
                continue  # pie subplots have no x/y axes to label
            if ax._xlabel:
                fig.update_xaxes(title_text=ax._xlabel, row=ax._row, col=ax._col)
            if ax._ylabel:
                fig.update_yaxes(title_text=ax._ylabel, row=ax._row, col=ax._col)

        shapes = self._collect_shapes()
        if shapes:
            fig.update_layout(shapes=shapes)

        return self._apply_layout(fig, done)

    def _build_empty_figure(self):
        flat = self._flat_axes()
        subplot_titles = [ax._title or "" for ax in flat]

        fig = make_subplots(
            rows=self._rows,
            cols=self._cols,
            subplot_titles=subplot_titles,
            specs=self._build_specs(),
        )
        for ax in flat:
            if ax._has_pie():
                continue  # pie subplots have no x/y axes to label
            if ax._xlabel:
                fig.update_xaxes(title_text=ax._xlabel, row=ax._row, col=ax._col)
            if ax._ylabel:
                fig.update_yaxes(title_text=ax._ylabel, row=ax._row, col=ax._col)

        shapes = self._collect_shapes()
        if shapes:
            fig.update_layout(shapes=shapes)

        return self._apply_layout(fig, done=False)

    def _update(self, t, done, var_index, *results):
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
        from ..expression import GroupBy
        from ..array import global_arraylist
        from ..midlevel import Program, group, each, accum, G

        # ------------------------------------------------------------------
        # Auto GroupBy CI: construct companion variables before BQ conversion
        # ------------------------------------------------------------------
        extra_vars = []
        for ax in self._flat_axes():
            for b in ax._bar_bindings:
                if b["ci"] is None or b["ci_var"] is not None:
                    continue  # no CI or explicit var/n provided — skip auto

                var = b["var"]
                if not isinstance(var, GroupBy):
                    raise ValueError(
                        "ci= without variance= and n= is only supported for "
                        "GroupBy variables.\n"
                        "For scalar variables, pass variance= and n= explicitly:\n"
                        "  ax.bar(mean, ci=0.95, variance=var, n=count)"
                    )

                arr = next(
                    (a for a in global_arraylist if a.id == int(var.array_index)),
                    None,
                )
                if arr is None:
                    raise ValueError(
                        f"Could not find array with id={var.array_index} "
                        "in global_arraylist."
                    )

                key_idx = var.group_index
                val_idx = _extract_gtoken_index(var.expr)
                if val_idx is None:
                    raise ValueError(
                        "Could not auto-detect the value tuple index from the "
                        "GroupBy expression. Pass variance= and n= explicitly."
                    )

                auto_count = group(each(arr, key_idx), accum(1))
                auto_ex2   = group(
                    each(arr, key_idx),
                    accum(each(G, val_idx) ** 2) / accum(1),
                )
                b["_auto_count_var"] = auto_count
                b["_auto_ex2_var"]   = auto_ex2
                extra_vars.extend([auto_count, auto_ex2])

        if extra_vars:
            program = Program(*program.args, *extra_vars)

        # ------------------------------------------------------------------
        # Validation: all bound vars must be in program.args
        # ------------------------------------------------------------------
        var_index = {id(v): i for i, v in enumerate(program.args)}

        for ax in self._flat_axes():
            for var in ax._get_all_vars():
                if id(var) not in var_index:
                    raise ValueError(
                        f"A variable bound to subplot (row={ax._row}, col={ax._col}) "
                        "was not found in program.args. "
                        "Make sure you pass the same variable objects to both "
                        "compile() and ax.line() / ax.scatter() / ax.bar()."
                    )

        self._display_handle = display(
            _fig_to_html(self._build_empty_figure()),
            display_id=True,
        )

        n_vars = len(program.args)

        def _update_wrapper(t, done, pct, *results):
            self._progress = pct
            self._elapsed_t = t
            self._update(t, done, var_index, *results)

        callback = _make_callback(n_vars, _update_wrapper)

        thread = threading.Thread(
            target=program.run,
            kwargs={"interval": interval, "callback": callback},
            daemon=True,
        )
        thread.start()
