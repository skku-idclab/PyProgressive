"""
pyprogressive.vis — Live progressive chart API.

Usage inside a program.run() loop::

    for state in program.run(interval=0.5):
        fig, ax = pp.vis.subplots()
        ax.line(state.value(mean), label="Mean")

    for state in program.run(interval=0.5):
        fig, (ax1, ax2) = pp.vis.subplots(1, 2)
        ax1.line(state.value(covXY), label="Cov")
        ax2.scatter(state.value(covXY), state.value(varX))
"""

try:
    import plotly.graph_objects as go
    import plotly.io as pio
    from plotly.subplots import make_subplots
    from IPython.display import display as _ipy_display, HTML
    _DEPS_AVAILABLE = True
except ImportError:
    _DEPS_AVAILABLE = False


def _require_deps():
    if not _DEPS_AVAILABLE:
        raise ImportError(
            "plotly is required.  Install with: pip install plotly"
        )


# ---------------------------------------------------------------------------
# LiveAxes — one subplot pane
# ---------------------------------------------------------------------------

class LiveAxes:
    """Accumulates chart data for a single subplot pane."""

    def __init__(self, row, col):
        self._row = row
        self._col = col
        # Accumulated series (line/scatter grow across ticks)
        self._line_series    = []   # [{'y': list, 'label': str}]
        self._scatter_series = []   # [{'x': list, 'y': list, 'label': str}]
        self._bar_series     = []   # [{'values': dict|scalar|None, 'label': str}]
        # Per-tick call counters
        self._line_call_idx    = 0
        self._scatter_call_idx = 0
        self._bar_call_idx     = 0
        # Snapshot charts (replaced each tick)
        self._pie_snapshot     = None  # {'values': dict, 'hole': float}
        self._heatmap_snapshot = None  # {'z': list, 'labels': list, ...}
        # Reference lines (reset each tick, re-declared in loop body)
        self._hlines = []   # [{'y': float, 'color': str, 'dash': str, 'width': float}]
        self._vlines = []   # [{'x': float, 'color': str, 'dash': str, 'width': float}]
        # Axis metadata
        self._title  = None
        self._xlabel = None
        self._ylabel = None
        self._ylim   = None

    # ------------------------------------------------------------------
    # Public chart methods (called inside the for loop body)
    # ------------------------------------------------------------------

    def line(self, value, label=None):
        """Append *value* to the line series for this tick.

        Multiple calls with the same axes object add separate lines,
        matched by call order across ticks.
        """
        idx = self._line_call_idx
        if idx >= len(self._line_series):
            self._line_series.append(
                {'y': [], 'label': label or f'series{idx}'}
            )
        self._line_series[idx]['y'].append(value)
        self._line_call_idx += 1

    def scatter(self, x, y, label=None):
        """Append the point (*x*, *y*) to the scatter series.

        Useful for tracking convergence trajectories.
        """
        idx = self._scatter_call_idx
        if idx >= len(self._scatter_series):
            self._scatter_series.append(
                {'x': [], 'y': [], 'label': label or f'scatter{idx}'}
            )
        self._scatter_series[idx]['x'].append(x)
        self._scatter_series[idx]['y'].append(y)
        self._scatter_call_idx += 1

    def bar(self, values, label=None):
        """Set the bar chart to the current *values* snapshot.

        *values* can be a dict ``{key: value}`` (GroupBy result) or a scalar.
        The chart always shows the latest snapshot.
        """
        idx = self._bar_call_idx
        if idx >= len(self._bar_series):
            self._bar_series.append(
                {'values': None, 'label': label or f'bar{idx}'}
            )
        self._bar_series[idx]['values'] = values
        self._bar_call_idx += 1

    def pie(self, values, hole=0.0, label=None):
        """Render *values* as a pie (or donut) chart snapshot.

        *values* should be a dict ``{key: value}`` (GroupBy result).
        *hole* controls the donut cutout: 0.0 = full pie, 0.4 = donut.
        """
        self._pie_snapshot = {
            'values': values,
            'hole': hole,
            'label': label,
        }

    def heatmap(self, z, labels=None, zmin=None, zmax=None,
                colorscale='RdBu', showscale=True):
        """Render a 2-D matrix *z* as a heatmap snapshot.

        *z* is a list-of-lists where each cell is a current scalar value
        (e.g. ``state.value(corr12)``).
        """
        # Deep-copy z so that mutable list objects are safely snapshotted
        self._heatmap_snapshot = {
            'z':          [[v for v in row] for row in z],
            'labels':     labels,
            'zmin':       zmin,
            'zmax':       zmax,
            'colorscale': colorscale,
            'showscale':  showscale,
        }

    def axhline(self, y, color='gray', linestyle='dash', linewidth=1):
        """Draw a horizontal reference line at *y* across the full subplot width."""
        self._hlines.append({'y': y, 'color': color,
                             'dash': linestyle, 'width': linewidth})

    def axvline(self, x, color='gray', linestyle='dash', linewidth=1):
        """Draw a vertical reference line at *x* across the full subplot height."""
        self._vlines.append({'x': x, 'color': color,
                             'dash': linestyle, 'width': linewidth})

    # ------------------------------------------------------------------
    # Axis labels / title
    # ------------------------------------------------------------------

    def set_title(self, text):   self._title  = text
    def set_xlabel(self, label): self._xlabel = label
    def set_ylabel(self, label): self._ylabel = label
    def set_ylim(self, lo, hi):  self._ylim   = (lo, hi)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _has_pie(self):
        return self._pie_snapshot is not None

    def _has_heatmap(self):
        return self._heatmap_snapshot is not None

    def _get_spec(self):
        if self._has_pie():
            return {'type': 'pie'}
        return {'type': 'xy'}

    def _reset_call_idx(self):
        """Reset per-tick state so the next tick starts fresh."""
        self._line_call_idx    = 0
        self._scatter_call_idx = 0
        self._bar_call_idx     = 0
        # Reference lines and snapshots are re-declared each tick
        self._hlines           = []
        self._vlines           = []
        self._pie_snapshot     = None
        self._heatmap_snapshot = None

    def _build_traces(self, t_history):
        """Return a list of Plotly traces for the current accumulated data."""
        traces = []

        # Line series (accumulated)
        for s in self._line_series:
            x = t_history[:len(s['y'])]
            traces.append(go.Scatter(
                x=list(x), y=list(s['y']),
                mode='lines', name=s['label'],
            ))

        # Scatter series (accumulated)
        for s in self._scatter_series:
            traces.append(go.Scatter(
                x=list(s['x']), y=list(s['y']),
                mode='markers', name=s['label'],
            ))

        # Bar series (snapshot)
        for s in self._bar_series:
            if s['values'] is None:
                continue
            v = s['values']
            if isinstance(v, dict):
                traces.append(go.Bar(
                    x=list(v.keys()), y=list(v.values()),
                    name=s['label'],
                ))
            else:
                traces.append(go.Bar(
                    x=['value'], y=[v],
                    name=s['label'],
                ))

        # Pie snapshot
        if self._pie_snapshot is not None:
            v = self._pie_snapshot['values']
            if isinstance(v, dict):
                traces.append(go.Pie(
                    labels=list(v.keys()),
                    values=list(v.values()),
                    hole=self._pie_snapshot['hole'],
                    showlegend=True,
                ))

        # Heatmap snapshot
        if self._heatmap_snapshot is not None:
            h = self._heatmap_snapshot
            kw = dict(
                z=h['z'],
                colorscale=h['colorscale'],
                showscale=h['showscale'],
                showlegend=False,
            )
            if h['labels']:
                kw['x'] = h['labels']
                kw['y'] = h['labels']
            if h['zmin'] is not None:
                kw['zmin'] = h['zmin']
            if h['zmax'] is not None:
                kw['zmax'] = h['zmax']
            traces.append(go.Heatmap(**kw))

        return traces

    def _get_shapes(self, xref, yref):
        """Return Plotly shape dicts for axhline / axvline."""
        shapes = []
        for h in self._hlines:
            shapes.append(dict(
                type='line', xref='paper', yref=yref,
                x0=0, x1=1, y0=h['y'], y1=h['y'],
                line=dict(color=h['color'], dash=h['dash'], width=h['width']),
            ))
        for v in self._vlines:
            shapes.append(dict(
                type='line', xref=xref, yref='paper',
                x0=v['x'], x1=v['x'], y0=0, y1=1,
                line=dict(color=v['color'], dash=v['dash'], width=v['width']),
            ))
        return shapes


# ---------------------------------------------------------------------------
# LiveFigure — subplot grid rendered to a single in-place Jupyter output
# ---------------------------------------------------------------------------

class LiveFigure:
    """Grid of LiveAxes subplots.  Rendered in-place on every tick."""

    def __init__(self, rows, cols, figsize=None):
        self._rows    = rows
        self._cols    = cols
        self._axes    = [
            [LiveAxes(r + 1, c + 1) for c in range(cols)]
            for r in range(rows)
        ]
        self._figsize   = figsize
        self._t_history = []
        self._handle    = None
        self._suptitle  = None

    def suptitle(self, text):
        """Set an overall title displayed above the progress bar."""
        self._suptitle = text

    def _flat_axes(self):
        return [ax for row in self._axes for ax in row]

    def _axes_for_unpack(self):
        """Return axes in matplotlib-compatible unpacking form."""
        if self._rows == 1 and self._cols == 1:
            return self._axes[0][0]
        if self._rows == 1:
            return self._axes[0]   # list → supports (ax1, ax2) = ...
        return self._axes          # 2-D list

    def _flush(self, t, done, progress):
        """Build/update the Plotly figure and push it to the Jupyter output."""
        _require_deps()

        self._t_history.append(t)
        flat = self._flat_axes()

        subplot_titles = [ax._title or '' for ax in flat]
        specs = [[ax._get_spec() for ax in row] for row in self._axes]

        fig = make_subplots(
            rows=self._rows,
            cols=self._cols,
            subplot_titles=subplot_titles,
            specs=specs,
        )

        for ax in flat:
            for trace in ax._build_traces(self._t_history):
                fig.add_trace(trace, row=ax._row, col=ax._col)
            if ax._has_pie():
                continue  # pie subplots have no xy axes
            if ax._xlabel:
                fig.update_xaxes(title_text=ax._xlabel,
                                 row=ax._row, col=ax._col)
            if ax._ylabel:
                fig.update_yaxes(title_text=ax._ylabel,
                                 row=ax._row, col=ax._col)
            if ax._ylim is not None:
                fig.update_yaxes(range=list(ax._ylim),
                                 row=ax._row, col=ax._col)

        # Reference lines (axhline / axvline)
        shapes = []
        for i, ax in enumerate(flat):
            if ax._has_pie():
                continue
            subplot_idx = i + 1
            xref = 'x' if subplot_idx == 1 else f'x{subplot_idx}'
            yref = 'y' if subplot_idx == 1 else f'y{subplot_idx}'
            shapes.extend(ax._get_shapes(xref, yref))
        if shapes:
            fig.update_layout(shapes=shapes)

        # Progress bar in the figure title
        BAR_WIDTH = 20
        filled  = BAR_WIDTH if done else int(progress * BAR_WIDTH)
        bar_str = '█' * filled + '░' * (BAR_WIDTH - filled)
        pct_int = 100 if done else int(progress * 100)
        suffix  = f'[{bar_str}] {pct_int}% | {t:.1f}s'
        if done:
            suffix += ' ✓'
        title_text = (f'{self._suptitle} — {suffix}'
                      if self._suptitle else suffix)

        layout_kw = {'title_text': title_text}
        if self._figsize is not None:
            layout_kw['width']  = self._figsize[0]
            layout_kw['height'] = self._figsize[1]
        fig.update_layout(**layout_kw)

        # Reset per-tick state on all axes AFTER building traces
        for ax in flat:
            ax._reset_call_idx()

        html = HTML(pio.to_html(fig, include_plotlyjs='cdn', full_html=False))
        if self._handle is None:
            self._handle = _ipy_display(html, display_id=True)
        else:
            self._handle.update(html)


# ---------------------------------------------------------------------------
# Module-level live state
# ---------------------------------------------------------------------------

_live_figure = None   # currently active LiveFigure, or None


def _live_reset():
    """Clear the active live figure (called by pp.reset())."""
    global _live_figure
    _live_figure = None


def _live_flush(t, done, progress):
    """Flush the active live figure (called by program.run() after each yield)."""
    if _live_figure is not None:
        _live_figure._flush(t, done, progress)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def subplots(nrows=1, ncols=1, figsize=None):
    """Create (or reuse) a live subplot grid.

    Call this *inside* a ``for state in program.run():`` loop.
    On each tick the same ``LiveFigure`` / ``LiveAxes`` objects are returned
    so that data accumulates across ticks.

    Parameters
    ----------
    nrows, ncols : int
        Grid dimensions.
    figsize : (width, height) in pixels, optional
        e.g. ``figsize=(1200, 500)``.

    Returns
    -------
    (fig, ax)               when nrows=1, ncols=1
    (fig, [ax0, ax1, ...])  when nrows=1, ncols>1
    (fig, [[ax00, ...], [ax10, ...]])  otherwise

    Example::

        for state in program.run(interval=0.5):
            fig, (ax1, ax2) = pp.vis.subplots(1, 2)
            ax1.line(state.value(mean),  label="Mean")
            ax2.scatter(state.value(covXY), state.value(varX))
    """
    global _live_figure
    if (_live_figure is None
            or _live_figure._rows != nrows
            or _live_figure._cols != ncols):
        _live_figure = LiveFigure(nrows, ncols, figsize=figsize)
    return _live_figure, _live_figure._axes_for_unpack()


def _single_ax():
    """Return the LiveAxes for a 1×1 live chart, creating it if needed."""
    _, ax = subplots(1, 1)
    return ax


def line(value, label=None, title=None, xlabel=None, ylabel=None, figsize=None):
    """Add a line data point to the single live chart.

    Shorthand for the common case of a single chart with one or more lines.
    Multiple ``pp.vis.line()`` calls in the same loop body add separate lines.

    Example::

        for state in program.run(interval=0.5):
            pp.vis.line(state.value(mean), label="Mean",    title="Stats",
                        xlabel="Elapsed (s)", ylabel="Value")
            pp.vis.line(state.value(var),  label="Variance")
    """
    _, ax = subplots(1, 1, figsize=figsize)
    if title:   ax.set_title(title)
    if xlabel:  ax.set_xlabel(xlabel)
    if ylabel:  ax.set_ylabel(ylabel)
    ax.line(value, label=label)


def scatter(x, y, label=None, title=None, xlabel=None, ylabel=None, figsize=None):
    """Add a scatter point to the single live chart.

    Example::

        for state in program.run(interval=0.5):
            pp.vis.scatter(state.value(covXY), state.value(varX),
                           xlabel="Cov", ylabel="Var")
    """
    _, ax = subplots(1, 1, figsize=figsize)
    if title:   ax.set_title(title)
    if xlabel:  ax.set_xlabel(xlabel)
    if ylabel:  ax.set_ylabel(ylabel)
    ax.scatter(x, y, label=label)


def bar(values, label=None, title=None, xlabel=None, ylabel=None, figsize=None):
    """Set the bar chart snapshot on the single live chart.

    *values* can be a dict ``{key: value}`` (GroupBy result) or a scalar.

    Example::

        for state in program.run(interval=0.5):
            pp.vis.bar(state.value(group_counts), label="Count", ylabel="N")
    """
    _, ax = subplots(1, 1, figsize=figsize)
    if title:   ax.set_title(title)
    if xlabel:  ax.set_xlabel(xlabel)
    if ylabel:  ax.set_ylabel(ylabel)
    ax.bar(values, label=label)
