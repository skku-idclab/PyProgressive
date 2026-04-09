import math

try:
    import plotly.graph_objects as go
    _PLOTLY_AVAILABLE = True
except ImportError:
    _PLOTLY_AVAILABLE = False


def _to_finite_float(raw):
    """Convert raw to float, returning None for NaN, Inf, complex, or any error."""
    try:
        val = float(raw)
        return None if not math.isfinite(val) else val
    except (TypeError, ValueError, OverflowError):
        return None


class ProgressiveAxes:
    """
    A single subplot panel, analogous to a matplotlib Axes.

    Bind progressive variables with line(), scatter(), or bar(), then configure
    with set_title / set_xlabel / set_ylabel / set_ylim before calling fig.run().

    Users never instantiate this directly — use pp.vis.subplots() instead.
    """

    def __init__(self, row, col):
        # 1-based grid position (Plotly convention)
        self._row = row
        self._col = col

        self._title = None
        self._xlabel = None
        self._ylabel = None
        self._ylim = None   # (ymin, ymax) or None

        # shared time axis for all line bindings on this axes
        self._history_t = []

        # [{var, label, history_v, style}]
        self._line_bindings = []

        # [{x_var, y_var, history_x, history_y}]
        self._scatter_bindings = []

        # [{var, label, current_val, style}]
        self._bar_bindings = []

    # ------------------------------------------------------------------
    # Public configuration API
    # ------------------------------------------------------------------

    def line(self, var, label=None, color=None, linewidth=None, linestyle=None):
        """
        Bind a progressive variable as a line on this axes.
        x-axis = elapsed computation time, y-axis = variable value.

        Args:
            var:       a PyProgressive variable (same object passed to compile())
            label:     legend label (optional)
            color:     line color, any CSS/hex string e.g. "red", "#1f77b4" (optional)
            linewidth: line width in pixels (optional)
            linestyle: "solid" | "dot" | "dash" | "longdash" | "dashdot" (optional)
        """
        self._line_bindings.append({
            "var": var,
            "label": label,
            "history_v": [],
            "style": {"color": color, "linewidth": linewidth, "linestyle": linestyle},
        })

    def scatter(self, x_var, y_var):
        """
        Bind two progressive variables as a convergence-trajectory scatter.
        The point (x_var, y_var) moves toward its final value over time.

        Args:
            x_var: variable for the x-axis
            y_var: variable for the y-axis
        """
        self._scatter_bindings.append({
            "x_var": x_var,
            "y_var": y_var,
            "history_x": [],
            "history_y": [],
        })

    def bar(self, var, label=None, color=None):
        """
        Bind a progressive variable as a bar chart (current-value snapshot).

        Two modes depending on the variable type at runtime:
        - GroupBy variable  → x = group keys, y = group values
        - Scalar variable   → a single bar showing the current value

        Calling bar() multiple times on the same axes adds grouped series.

        Args:
            var:   a PyProgressive variable (same object passed to compile())
            label: bar series label (optional)
            color: bar color, any CSS/hex string (optional)
        """
        self._bar_bindings.append({
            "var": var,
            "label": label,
            "current_val": None,
            "style": {"color": color},
        })

    def set_title(self, text):
        self._title = text

    def set_xlabel(self, text):
        self._xlabel = text

    def set_ylabel(self, text):
        self._ylabel = text

    def set_ylim(self, ymin, ymax):
        """Fix the y-axis range.  Useful for e.g. correlation plots: set_ylim(-1, 1)."""
        self._ylim = (ymin, ymax)

    # ------------------------------------------------------------------
    # Internal helpers (called by ProgressiveFigure)
    # ------------------------------------------------------------------

    def _get_all_vars(self):
        """Return all variable objects bound to this axes (for validation)."""
        vars_ = []
        for b in self._line_bindings:
            vars_.append(b["var"])
        for b in self._scatter_bindings:
            vars_.append(b["x_var"])
            vars_.append(b["y_var"])
        for b in self._bar_bindings:
            vars_.append(b["var"])
        return vars_

    def _has_bar(self):
        return len(self._bar_bindings) > 0

    def _append(self, t, var_index, results):
        """
        Append one tick of data.  Called per callback tick by ProgressiveFigure.

        Args:
            t:         elapsed time (float)
            var_index: {id(var): index_in_results} built by ProgressiveFigure
            results:   tuple of callback result values
        """
        self._history_t.append(t)

        for b in self._line_bindings:
            raw = results[var_index[id(b["var"])]]
            b["history_v"].append(None if isinstance(raw, dict) else _to_finite_float(raw))

        for b in self._scatter_bindings:
            xi = var_index[id(b["x_var"])]
            yi = var_index[id(b["y_var"])]
            b["history_x"].append(_to_finite_float(results[xi]))
            b["history_y"].append(_to_finite_float(results[yi]))

        for b in self._bar_bindings:
            raw = results[var_index[id(b["var"])]]
            b["current_val"] = raw if isinstance(raw, dict) else _to_finite_float(raw)

    def _build_traces(self):
        """
        Return a list of traces (go.Scatter or go.Bar) for this axes.
        Called by ProgressiveFigure._build_figure() on every tick.
        """
        traces = []

        # --- line traces ---
        for i, b in enumerate(self._line_bindings):
            lbl = b["label"] if b["label"] is not None else f"var{i}"
            valid = [(t, v) for t, v in zip(self._history_t, b["history_v"]) if v is not None]
            xs = [p[0] for p in valid]
            ys = [p[1] for p in valid]
            s = b["style"]
            line_kwargs = {}
            if s["color"] is not None:
                line_kwargs["color"] = s["color"]
            if s["linewidth"] is not None:
                line_kwargs["width"] = s["linewidth"]
            if s["linestyle"] is not None:
                line_kwargs["dash"] = s["linestyle"]
            traces.append(go.Scatter(
                x=xs, y=ys, mode="lines", name=lbl,
                line=line_kwargs if line_kwargs else None,
            ))

        # --- scatter traces ---
        for b in self._scatter_bindings:
            hx = b["history_x"]
            hy = b["history_y"]
            valid = [(x, y) for x, y in zip(hx, hy) if x is not None and y is not None]
            vx = [p[0] for p in valid]
            vy = [p[1] for p in valid]
            traces.append(go.Scatter(
                x=vx, y=vy,
                mode="lines",
                name="trajectory",
                line=dict(color="lightblue", width=1.5),
                showlegend=False,
            ))
            if vx:
                traces.append(go.Scatter(
                    x=[vx[-1]], y=[vy[-1]],
                    mode="markers",
                    name="current",
                    marker=dict(color="crimson", size=10),
                    showlegend=False,
                ))

        # --- bar traces ---
        for i, b in enumerate(self._bar_bindings):
            val = b["current_val"]
            if val is None:
                continue
            lbl = b["label"] if b["label"] is not None else f"bar{i}"
            if isinstance(val, dict):
                x_vals = [str(k) for k in val.keys()]
                y_vals = list(val.values())
            else:
                x_vals = [lbl]
                y_vals = [val]
            marker_kwargs = {}
            if b["style"]["color"] is not None:
                marker_kwargs["color"] = b["style"]["color"]
            traces.append(go.Bar(
                x=x_vals, y=y_vals, name=lbl,
                marker=marker_kwargs if marker_kwargs else None,
            ))

        return traces
