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
        self._showlegend = True

    # ------------------------------------------------------------------
    # Public configuration API
    # ------------------------------------------------------------------

    def suptitle(self, text):
        """Set an overall title for the entire figure (above all subplots)."""
        self._suptitle = text

    def legend(self, show):
        """Show or hide the figure legend.  Pass False to hide all legends."""
        self._showlegend = bool(show)

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

        if not self._showlegend:
            layout_kwargs["showlegend"] = False

        if layout_kwargs:
            fig.update_layout(**layout_kwargs)

        for ax in flat:
            if ax._has_pie():
                continue  # no y-axis on pie subplots
            if ax._ylim is not None:
                fig.update_yaxes(range=list(ax._ylim), row=ax._row, col=ax._col)

        return fig

    def _h_spacing(self, flat):
        """Compute horizontal_spacing for make_subplots.

        When any non-rightmost column contains a colorbar trace, we widen the
        gap so that the colorbar (repositioned into the gap) does not overlap
        with the adjacent subplot's tick labels or legend.  Otherwise we use
        Plotly's default (0.2 / ncols).
        """
        default = 0.2 / self._cols
        if self._cols <= 1:
            return default
        has_midcol_colorbar = any(
            ax._col < self._cols and ax._has_colorbar()
            for ax in flat
        )
        return 0.18 if has_midcol_colorbar else default

    def _subplot_domain(self, fig, trace):
        """Return (domain_x, domain_y) for the subplot that owns *trace*.

        domain_x / domain_y are [min, max] in paper coordinates [0, 1].
        Returns (None, None) if the domain cannot be determined.
        """
        xaxis_ref = getattr(trace, 'xaxis', None)
        if xaxis_ref:
            suffix = xaxis_ref[1:]          # 'x' -> '', 'x2' -> '2'
            x_key = 'xaxis' + suffix
            y_key = 'yaxis' + suffix
            try:
                return (list(fig.layout[x_key].domain),
                        list(fig.layout[y_key].domain))
            except Exception:
                pass
        # Pie traces store their domain directly on the trace
        domain_attr = getattr(trace, 'domain', None)
        if domain_attr is not None:
            try:
                return (list(domain_attr.x), list(domain_attr.y))
            except Exception:
                pass
        return (None, None)

    def _reposition_subplot_legends(self, fig, ax_trace_ranges, flat):
        """Give each subplot its own legend, placed just outside its plot area.

        Only subplots that have explicit user-supplied labels AND have not had
        their legend suppressed (ax.legend(False)) are processed.  Each such
        subplot's x-domain is shrunk to free space on the right, and the
        legend is positioned in that freed space — no data overlap.

        Only active when self._cols > 1; single-column figures use Plotly's
        default placement.  Requires Plotly 5.x (legend2 / legend3 … support).
        """
        if self._cols <= 1 or not self._showlegend:
            return

        LEGEND_WIDTH = 0.12   # fraction of figure width reserved per legend

        legend_counter = 0
        layout_updates = {}

        for ax in flat:
            if not ax._showlegend:
                continue

            start, end = ax_trace_ranges[id(ax)]
            if start == end:
                continue

            # Find the subplot domain via the first trace that actually shows
            # in the legend (showlegend is not explicitly False).
            # Traces like go.Heatmap have showlegend=False set explicitly, so
            # they are skipped here.  If every trace is False, domain_x stays
            # None and the axes is skipped entirely (no domain shrink).
            domain_x, domain_y = None, None
            xaxis_suffix = None
            for i in range(start, end):
                trace = fig.data[i]
                if trace.showlegend is False:
                    continue
                domain_x, domain_y = self._subplot_domain(fig, trace)
                xaxis_ref = getattr(trace, 'xaxis', None)
                if xaxis_ref:
                    xaxis_suffix = xaxis_ref[1:]   # 'x' -> '', 'x2' -> '2'
                if domain_x is not None:
                    break

            if domain_x is None:
                continue

            # Shrink this subplot's x-domain to make room for the legend
            new_x_end = domain_x[1] - LEGEND_WIDTH
            if xaxis_suffix is not None:
                layout_updates['xaxis' + xaxis_suffix] = dict(
                    domain=[domain_x[0], new_x_end]
                )

            # Place the named legend just to the right of the shrunken domain
            legend_name = 'legend' if legend_counter == 0 else f'legend{legend_counter + 1}'
            layout_updates[legend_name] = dict(
                x=new_x_end + 0.01,
                xanchor='left',
                y=domain_y[1] if domain_y else 1.0,
                yanchor='top',
                bgcolor='rgba(255,255,255,0.8)',
                bordercolor='rgba(0,0,0,0.15)',
                borderwidth=1,
            )

            for i in range(start, end):
                if fig.data[i].showlegend is not False:
                    fig.data[i].update(legend=legend_name)

            legend_counter += 1

        if layout_updates:
            fig.update_layout(**layout_updates)

    def _build_figure(self, done):
        flat = self._flat_axes()
        subplot_titles = [ax._title or "" for ax in flat]

        fig = make_subplots(
            rows=self._rows,
            cols=self._cols,
            subplot_titles=subplot_titles,
            specs=self._build_specs(),
            horizontal_spacing=self._h_spacing(flat),
        )

        # Add traces and record which trace indices belong to each axes
        ax_trace_ranges = {}
        for ax in flat:
            start = len(fig.data)
            for trace in ax._build_traces():
                fig.add_trace(trace, row=ax._row, col=ax._col)
            ax_trace_ranges[id(ax)] = (start, len(fig.data))

            if ax._has_pie():
                continue  # pie subplots have no x/y axes to label
            if ax._xlabel:
                fig.update_xaxes(title_text=ax._xlabel, row=ax._row, col=ax._col)
            if ax._ylabel:
                fig.update_yaxes(title_text=ax._ylabel, row=ax._row, col=ax._col)

        shapes = self._collect_shapes()
        if shapes:
            fig.update_layout(shapes=shapes)

        # Reposition colorbars to appear immediately right of their own subplot
        # (mirrors matplotlib's fig.colorbar(im, ax=ax) behaviour).
        if self._cols > 1:
            for i, trace in enumerate(fig.data):
                if not getattr(trace, 'showscale', False):
                    continue
                xaxis_ref = getattr(trace, 'xaxis', None) or 'x'
                axis_key = 'xaxis' + xaxis_ref[1:]
                domain = fig.layout[axis_key].domain
                fig.data[i].update(colorbar=dict(
                    x=domain[1] + 0.01,
                    xanchor='left',
                    thickness=15,
                ))

        # Position each subplot's legend inside that subplot
        self._reposition_subplot_legends(fig, ax_trace_ranges, flat)

        return self._apply_layout(fig, done)

    def _build_empty_figure(self):
        flat = self._flat_axes()
        subplot_titles = [ax._title or "" for ax in flat]

        fig = make_subplots(
            rows=self._rows,
            cols=self._cols,
            subplot_titles=subplot_titles,
            specs=self._build_specs(),
            horizontal_spacing=self._h_spacing(flat),
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
