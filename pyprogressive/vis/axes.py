import math

try:
    import plotly.graph_objects as go
    _PLOTLY_AVAILABLE = True
except ImportError:
    _PLOTLY_AVAILABLE = False


# ---------------------------------------------------------------------------
# CI helpers
# ---------------------------------------------------------------------------

_Z_SCORES = {0.90: 1.645, 0.95: 1.960, 0.99: 2.576}


def _z_score(ci):
    if ci in _Z_SCORES:
        return _Z_SCORES[ci]
    raise ValueError(
        f"Unsupported confidence level: {ci}. "
        f"Supported values: {sorted(_Z_SCORES.keys())}"
    )


def _ci_half(ci_level, var_val, n_val):
    """Return CI half-width (float or dict), or None when inputs are invalid."""
    z = _z_score(ci_level)
    if isinstance(var_val, dict) and isinstance(n_val, dict):
        result = {}
        for k in var_val:
            if k in n_val:
                v, cnt = var_val[k], n_val[k]
                if v is not None and cnt is not None and v >= 0 and cnt > 0:
                    result[k] = z * math.sqrt(v) / math.sqrt(cnt)
        return result if result else None
    try:
        v, cnt = float(var_val), float(n_val)
        if v < 0 or cnt <= 0:
            return None
        return z * math.sqrt(v) / math.sqrt(cnt)
    except Exception:
        return None


_LINESTYLE_MAP = {
    # Plotly names (pass-through)
    "solid":    "solid",
    "dot":      "dot",
    "dash":     "dash",
    "longdash": "longdash",
    "dashdot":  "dashdot",
    # matplotlib shortcuts
    "-":        "solid",
    "--":       "dash",
    ":":        "dot",
    "-.":       "dashdot",
}


def _linestyle_to_plotly(s):
    """Convert a linestyle string (matplotlib or Plotly) to a Plotly dash value."""
    result = _LINESTYLE_MAP.get(s)
    if result is None:
        raise ValueError(
            f"Unsupported linestyle: {repr(s)}. "
            f"Supported: {sorted(_LINESTYLE_MAP.keys())}"
        )
    return result


def _to_finite_float(raw):
    """Convert raw to float, returning None for NaN, Inf, complex, or any error."""
    try:
        val = float(raw)
        return None if not math.isfinite(val) else val
    except (TypeError, ValueError, OverflowError):
        return None


# ---------------------------------------------------------------------------
# ProgressiveAxes
# ---------------------------------------------------------------------------

class ProgressiveAxes:
    """
    A single subplot panel, analogous to a matplotlib Axes.

    Bind progressive variables with line(), scatter(), or bar(), then configure
    with set_title / set_xlabel / set_ylabel / set_ylim before calling fig.run().

    Users never instantiate this directly — use pp.vis.subplots() instead.
    """

    def __init__(self, row, col):
        self._row = row
        self._col = col

        self._title = None
        self._xlabel = None
        self._ylabel = None
        self._ylim = None
        self._showlegend = True

        self._history_t = []
        self._line_bindings = []
        self._scatter_bindings = []
        self._bar_bindings = []
        self._heatmap_bindings = []
        self._pie_bindings = []
        self._axhlines = []
        self._axvlines = []

    # ------------------------------------------------------------------
    # Public configuration API
    # ------------------------------------------------------------------

    def line(self, var, label=None, color=None, linewidth=None, linestyle=None,
             ci=None, variance=None, n=None):
        """
        Bind a progressive variable as a line on this axes.

        Args:
            var:       PyProgressive variable (same object passed to compile())
            label:     legend label (optional)
            color:     CSS/hex color string (optional)
            linewidth: line width in pixels (optional)
            linestyle: "solid" | "dot" | "dash" | "longdash" | "dashdot" (optional)
            ci:        confidence level — 0.90, 0.95, or 0.99 (optional).
                       When set, draws a fill band around the line.
                       Requires variance= and n=.
            variance:  variance variable compiled alongside var (required when ci is set)
            n:         sample-count variable compiled alongside var (required when ci is set)
        """
        if ci is not None:
            if variance is None or n is None:
                raise ValueError(
                    "ci= requires variance= and n= to be passed as well.\n"
                    "Example:\n"
                    "  count = accum(1)\n"
                    "  var   = accum((each(data) - mean)**2) / len(data)\n"
                    "  ax.line(mean, ci=0.95, variance=var, n=count)"
                )
            _z_score(ci)  # validate early
        self._line_bindings.append({
            "var": var,
            "label": label,
            "history_v": [],
            "history_ci_lower": [],
            "history_ci_upper": [],
            "style": {"color": color, "linewidth": linewidth, "linestyle": linestyle},
            "ci": ci,
            "ci_var": variance,
            "ci_n": n,
        })

    def scatter(self, x_var, y_var):
        """
        Bind two progressive variables as a convergence-trajectory scatter.

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

    def bar(self, var, label=None, color=None, ci=None, variance=None, n=None):
        """
        Bind a progressive variable as a bar chart (current-value snapshot).

        Modes:
        - GroupBy variable  → x = group keys, y = group values
        - Scalar variable   → a single bar showing the current value

        Calling bar() multiple times on the same axes adds grouped series.

        Args:
            var:      PyProgressive variable (same object passed to compile())
            label:    bar series label (optional)
            color:    CSS/hex color string (optional)
            ci:       confidence level — 0.90, 0.95, or 0.99 (optional).
                      When set on a GroupBy variable, error bars are added
                      automatically (no extra compile needed).
                      For scalar variables, variance= and n= are required.
            variance: variance variable (required for scalar CI, optional for GroupBy)
            n:        count variable (required for scalar CI, optional for GroupBy)
        """
        if ci is not None:
            _z_score(ci)  # validate early
        self._bar_bindings.append({
            "var": var,
            "label": label,
            "current_val": None,
            "current_ci_err": None,
            "style": {"color": color},
            "ci": ci,
            "ci_var": variance,
            "ci_n": n,
            "_auto_ex2_var": None,     # filled by ProgressiveFigure.run()
            "_auto_count_var": None,   # filled by ProgressiveFigure.run()
        })

    def heatmap(self, var_grid, labels=None, xlabels=None, ylabels=None,
                zmin=None, zmax=None, colorscale=None, showscale=True):
        """
        Bind a 2-D grid of progressive variables as a heatmap (current-value snapshot).

        Each cell in var_grid is either a PyProgressive variable (same object
        passed to compile()) or a numeric constant (e.g. 1 for a diagonal).

        Args:
            var_grid:   2-D list of Variable / numeric constant
            labels:     symmetric axis labels — used for both x and y when
                        xlabels / ylabels are not given (optional)
            xlabels:    column labels, length must equal ncols (optional)
            ylabels:    row labels, length must equal nrows (optional)
            zmin:       minimum of the color scale (optional, e.g. -1)
            zmax:       maximum of the color scale (optional, e.g.  1)
            colorscale: Plotly colorscale name (default "RdBu")
            showscale:  whether to show the colorscale bar (default True)

        Example::

            corr12 = cov12 / pp.sqrt(var1 * var2)
            corr13 = cov13 / pp.sqrt(var1 * var3)
            corr23 = cov23 / pp.sqrt(var2 * var3)

            program = pp.compile(cov12, cov13, cov23, var1, var2, var3,
                                 corr12, corr13, corr23)

            fig, ax = pp.vis.subplots()
            ax.heatmap(
                [[1,       corr12, corr13],
                 [corr12,  1,      corr23],
                 [corr13,  corr23, 1     ]],
                labels=["X1", "X2", "X3"],
                zmin=-1, zmax=1,
            )
            fig.run(program, interval=0.3)
        """
        self._heatmap_bindings.append({
            "var_grid":   var_grid,
            "xlabels":    xlabels if xlabels is not None else labels,
            "ylabels":    ylabels if ylabels is not None else labels,
            "zmin":       zmin,
            "zmax":       zmax,
            "colorscale": colorscale or "RdBu",
            "showscale":  showscale,
            "current_matrix": None,
        })

    def pie(self, var, hole=0.0, colors=None):
        """
        Bind a progressive variable as a pie (or donut) chart.

        Two modes depending on the type of var:

        **GroupBy variable** (most common)
            Group keys become slice labels; group values become slice sizes.
            The chart updates as a snapshot on every tick.

        **Scalar variable**
            Each call to pie() on the same axes adds one slice.
            The slice label is taken from the variable's compile-time label if
            set, otherwise "slice<i>".  Pass label= via compile() or use
            multiple GroupBy keys instead.

        Args:
            var:    PyProgressive variable (GroupBy or scalar).
                    Same object that was passed to compile().
            hole:   Fraction of the radius to cut out for a donut chart.
                    0.0 = full pie (default), 0.4 = donut.
            colors: List of CSS/hex color strings, one per slice (optional).

        Examples::

            # --- GroupBy: group counts as a pie ---
            group_count = group(each(data, 0), accum(1))
            program = pp.compile(group_count)

            fig, ax = pp.vis.subplots()
            ax.pie(group_count)
            fig.run(program, interval=0.1)

            # --- Donut ---
            ax.pie(group_mean, hole=0.4)

            # --- Multiple scalar slices ---
            count_a = accum(...)
            count_b = accum(...)
            program = pp.compile(count_a, count_b)

            ax.pie(count_a, label="A")  # not yet; use GroupBy for this case
        """
        if not (0.0 <= hole < 1.0):
            raise ValueError("hole must be in [0.0, 1.0).")
        self._pie_bindings.append({
            "var":         var,
            "hole":        hole,
            "colors":      colors,
            "current_val": None,
        })

    def set_title(self, text):
        self._title = text

    def set_xlabel(self, text):
        self._xlabel = text

    def set_ylabel(self, text):
        self._ylabel = text

    def legend(self, show):
        """Show or hide the legend for this subplot.  Pass False to hide."""
        self._showlegend = bool(show)

    def axhline(self, y, color="gray", linewidth=1, linestyle="dash"):
        """
        Draw a horizontal reference line across the full width of this subplot.

        Args:
            y:         y-axis value at which to draw the line
            color:     CSS/hex color string (default "gray")
            linewidth: line width in pixels (default 1)
            linestyle: "solid" | "dot" | "dash" | "longdash" | "dashdot"
                       or matplotlib shortcuts "-" | "--" | ":" | "-."
                       (default "dash")

        Example::

            ax.line(corr, label="Corr(X,Y)")
            ax.axhline(0,    color="gray",  linestyle="dash")   # zero baseline
            ax.axhline(0.5,  color="green", linestyle="dot")    # reference value
            ax.set_ylim(-1, 1)
        """
        self._axhlines.append({
            "y":         y,
            "color":     color,
            "linewidth": linewidth,
            "linestyle": _linestyle_to_plotly(linestyle),
        })

    def axvline(self, x, color="gray", linewidth=1, linestyle="dash"):
        """
        Draw a vertical reference line across the full height of this subplot.

        The x coordinate is in elapsed-time seconds (same scale as the x-axis
        of line / scatter charts).

        Args:
            x:         x-axis value (elapsed time in seconds)
            color:     CSS/hex color string (default "gray")
            linewidth: line width in pixels (default 1)
            linestyle: "solid" | "dot" | "dash" | "longdash" | "dashdot"
                       or matplotlib shortcuts "-" | "--" | ":" | "-."
                       (default "dash")

        Example::

            ax.line(mean, label="Mean")
            ax.axvline(1.0, color="red", linestyle="dot")   # mark t=1 s
        """
        self._axvlines.append({
            "x":         x,
            "color":     color,
            "linewidth": linewidth,
            "linestyle": _linestyle_to_plotly(linestyle),
        })

    def set_ylim(self, ymin, ymax):
        """Fix the y-axis range.  Useful e.g. for correlation: set_ylim(-1, 1)."""
        self._ylim = (ymin, ymax)

    # ------------------------------------------------------------------
    # Internal helpers (called by ProgressiveFigure)
    # ------------------------------------------------------------------

    def _get_all_vars(self):
        """Return all variable objects bound to this axes (for validation)."""
        vars_ = []
        for b in self._line_bindings:
            vars_.append(b["var"])
            if b["ci_var"] is not None:
                vars_.append(b["ci_var"])
            if b["ci_n"] is not None:
                vars_.append(b["ci_n"])
        for b in self._scatter_bindings:
            vars_.append(b["x_var"])
            vars_.append(b["y_var"])
        for b in self._bar_bindings:
            vars_.append(b["var"])
            if b["ci_var"] is not None:
                vars_.append(b["ci_var"])
            if b["ci_n"] is not None:
                vars_.append(b["ci_n"])
            if b["_auto_ex2_var"] is not None:
                vars_.append(b["_auto_ex2_var"])
            if b["_auto_count_var"] is not None:
                vars_.append(b["_auto_count_var"])
        for b in self._heatmap_bindings:
            for row in b["var_grid"]:
                for cell in row:
                    if not isinstance(cell, (int, float)):
                        vars_.append(cell)
        for b in self._pie_bindings:
            vars_.append(b["var"])
        return vars_

    def _has_bar(self):
        return len(self._bar_bindings) > 0

    def _has_pie(self):
        return len(self._pie_bindings) > 0

    def _has_colorbar(self):
        """Return True if this axes has any trace that will show a colorscale bar."""
        return any(b.get('showscale', True) for b in self._heatmap_bindings)

    def _has_explicit_labels(self):
        """Return True if any bound trace has a user-provided label.

        Used by ProgressiveFigure to decide whether to allocate legend space
        for this subplot.  Heatmap / pie are excluded because they do not
        produce conventional legend entries.
        """
        return (
            any(b["label"] is not None for b in self._line_bindings) or
            any(b["label"] is not None for b in self._scatter_bindings) or
            any(b["label"] is not None for b in self._bar_bindings)
        )

    def _get_shapes(self, xref, yref):
        """Return Plotly shape dicts for axhline / axvline on this subplot.

        xref / yref are the Plotly axis references for this subplot
        (e.g. "x", "y" for the first; "x2", "y2" for the second, etc.).
        """
        shapes = []
        for h in self._axhlines:
            shapes.append(dict(
                type="line",
                # span the full subplot width using the axis domain
                x0=0, x1=1, xref=f"{xref} domain",
                y0=h["y"], y1=h["y"], yref=yref,
                line=dict(color=h["color"], width=h["linewidth"], dash=h["linestyle"]),
            ))
        for v in self._axvlines:
            shapes.append(dict(
                type="line",
                x0=v["x"], x1=v["x"], xref=xref,
                # span the full subplot height using the axis domain
                y0=0, y1=1, yref=f"{yref} domain",
                line=dict(color=v["color"], width=v["linewidth"], dash=v["linestyle"]),
            ))
        return shapes

    def _append(self, t, var_index, results):
        """Append one tick of data. Called per callback tick by ProgressiveFigure."""
        self._history_t.append(t)

        # --- line ---
        for b in self._line_bindings:
            raw = results[var_index[id(b["var"])]]
            val = None if isinstance(raw, dict) else _to_finite_float(raw)
            b["history_v"].append(val)

            if b["ci"] is not None:
                var_val = results[var_index[id(b["ci_var"])]]
                n_val   = results[var_index[id(b["ci_n"])]]
                hw = _ci_half(b["ci"], var_val, n_val)
                center = val
                if hw is not None and center is not None and not isinstance(hw, dict):
                    b["history_ci_lower"].append(center - hw)
                    b["history_ci_upper"].append(center + hw)
                else:
                    b["history_ci_lower"].append(None)
                    b["history_ci_upper"].append(None)

        # --- scatter ---
        for b in self._scatter_bindings:
            b["history_x"].append(_to_finite_float(results[var_index[id(b["x_var"])]]))
            b["history_y"].append(_to_finite_float(results[var_index[id(b["y_var"])]]))

        # --- bar ---
        for b in self._bar_bindings:
            raw = results[var_index[id(b["var"])]]
            b["current_val"] = raw if isinstance(raw, dict) else _to_finite_float(raw)

            if b["ci"] is not None:
                if b["ci_var"] is not None:
                    # explicit var/n
                    var_val = results[var_index[id(b["ci_var"])]]
                    n_val   = results[var_index[id(b["ci_n"])]]
                else:
                    # GroupBy auto: var[k] = E[X^2][k] - E[X][k]^2
                    ex2_val  = results[var_index[id(b["_auto_ex2_var"])]]
                    mean_val = b["current_val"]
                    n_val    = results[var_index[id(b["_auto_count_var"])]]
                    if isinstance(ex2_val, dict) and isinstance(mean_val, dict):
                        var_val = {
                            k: ex2_val[k] - mean_val[k] ** 2
                            for k in mean_val
                            if k in ex2_val
                            and mean_val[k] is not None
                            and ex2_val[k] is not None
                        }
                    else:
                        var_val = None
                b["current_ci_err"] = _ci_half(b["ci"], var_val, n_val) if var_val is not None else None

        # --- pie ---
        for b in self._pie_bindings:
            raw = results[var_index[id(b["var"])]]
            b["current_val"] = raw if isinstance(raw, dict) else _to_finite_float(raw)

        # --- heatmap ---
        for b in self._heatmap_bindings:
            matrix = []
            for row in b["var_grid"]:
                row_vals = []
                for cell in row:
                    if isinstance(cell, (int, float)):
                        row_vals.append(float(cell))
                    elif id(cell) in var_index:
                        row_vals.append(_to_finite_float(results[var_index[id(cell)]]))
                    else:
                        row_vals.append(None)
                matrix.append(row_vals)
            b["current_matrix"] = matrix

    def _build_traces(self):
        """Return traces for this axes. Called by ProgressiveFigure._build_figure()."""
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

            # CI fill band (upper trace first, then lower with fill="tonexty")
            if b["ci"] is not None and b["history_ci_upper"]:
                uppers = [(t, v) for t, v in zip(self._history_t, b["history_ci_upper"]) if v is not None]
                lowers = [(t, v) for t, v in zip(self._history_t, b["history_ci_lower"]) if v is not None]
                if uppers and lowers:
                    fill_color = "rgba(100,149,237,0.2)"
                    # Use line color if provided
                    if s["color"] is not None:
                        # build rgba from named color — fallback to default blue
                        fill_color = "rgba(100,149,237,0.2)"
                    traces.append(go.Scatter(
                        x=[p[0] for p in uppers], y=[p[1] for p in uppers],
                        mode="lines", line=dict(width=0),
                        showlegend=False, hoverinfo="skip",
                    ))
                    traces.append(go.Scatter(
                        x=[p[0] for p in lowers], y=[p[1] for p in lowers],
                        mode="lines", fill="tonexty",
                        fillcolor=fill_color, line=dict(width=0),
                        showlegend=False, hoverinfo="skip",
                        name=f"{lbl} {int(b['ci'] * 100)}% CI",
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

            # error bars
            error_y = None
            err = b["current_ci_err"]
            if err is not None:
                if isinstance(val, dict) and isinstance(err, dict):
                    error_array = [err.get(str(k), 0) for k in val.keys()]
                    error_y = dict(type="data", array=error_array, visible=True)
                elif not isinstance(err, dict):
                    error_y = dict(type="data", array=[err], visible=True)

            marker_kwargs = {}
            if b["style"]["color"] is not None:
                marker_kwargs["color"] = b["style"]["color"]
            traces.append(go.Bar(
                x=x_vals, y=y_vals, name=lbl,
                showlegend=b["label"] is not None,
                marker=marker_kwargs if marker_kwargs else None,
                error_y=error_y,
            ))

        # --- pie traces ---
        # Collect all pie bindings for this axes into one go.Pie trace.
        # GroupBy vars  → keys = labels, values = sizes
        # Scalar vars   → each binding contributes one slice
        pie_labels = []
        pie_values = []
        pie_hole   = 0.0
        pie_colors = None

        for i, b in enumerate(self._pie_bindings):
            val = b["current_val"]
            if val is None:
                continue
            pie_hole = b["hole"]  # last binding wins (all should match)
            if b["colors"] is not None:
                pie_colors = b["colors"]

            if isinstance(val, dict):
                pie_labels.extend([str(k) for k in val.keys()])
                pie_values.extend([v for v in val.values()])
            else:
                pie_labels.append(f"slice{i}")
                pie_values.append(val)

        if pie_values:
            pie_kwargs = dict(
                labels=pie_labels,
                values=pie_values,
                hole=pie_hole,
                textinfo="label+percent",
                showlegend=False,   # labels already shown on slices via textinfo
            )
            if pie_colors is not None:
                pie_kwargs["marker"] = dict(colors=pie_colors)
            traces.append(go.Pie(**pie_kwargs))

        # --- heatmap traces ---
        for b in self._heatmap_bindings:
            if b["current_matrix"] is None:
                continue
            kwargs = dict(
                z=b["current_matrix"],
                colorscale=b["colorscale"],
                showscale=b["showscale"],
            )
            if b["xlabels"] is not None:
                kwargs["x"] = b["xlabels"]
            if b["ylabels"] is not None:
                kwargs["y"] = b["ylabels"]
            if b["zmin"] is not None:
                kwargs["zmin"] = b["zmin"]
            if b["zmax"] is not None:
                kwargs["zmax"] = b["zmax"]
            if b["zmin"] is not None and b["zmax"] is not None:
                kwargs["zmid"] = (b["zmin"] + b["zmax"]) / 2
            traces.append(go.Heatmap(showlegend=False, **kwargs))

        if not self._showlegend:
            for trace in traces:
                trace.update(showlegend=False)

        return traces
