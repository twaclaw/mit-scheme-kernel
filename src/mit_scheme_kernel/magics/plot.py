"""Render scmutils plots inline, as SVG, using matplotlib.

scmutils draws through X11, which a notebook has no access to. `plotting.scm`
replaces the graphics primitives so drawing is recorded instead, and emits it
between `MITKPLOT<<` markers. This module turns that back into a figure.

The wire format is line oriented rather than JSON because MIT Scheme prints
flonums as ".5" and "1.", which JSON rejects and `float()` accepts:

    FRAME xmin xmax ymin ymax
    POINTS x y x y ...
    LINE x0 y0 x1 y1
    TEXT x y label
"""

from __future__ import annotations

import base64
import io
import re
from dataclasses import dataclass, field

from metakernel import Magic, option

# The REPL runs behind a pty, so line endings arrive as \r\n.
PLOT_PAYLOAD_RE = re.compile(r"MITKPLOT<<\r?\n(.*?)>>MITKPLOT", re.DOTALL)
EMIT_COMMAND = "(mitk:emit-plots)"

MATPLOTLIB_MISSING = "Inline plotting needs matplotlib, which is not installed.\n    pip install 'mit-scheme-kernel[plot]'"


@dataclass
class Frame:
    """One scmutils graphics device, with everything drawn on it."""

    xmin: float = 0.0
    xmax: float = 1.0
    ymin: float = 0.0
    ymax: float = 1.0
    polylines: list[tuple[list[float], list[float]]] = field(default_factory=list)
    points: list[tuple[list[float], list[float]]] = field(default_factory=list)
    texts: list[tuple[float, float, str]] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (self.polylines or self.points or self.texts)


def parse_payload(text: str) -> list[Frame]:
    """Read the emitted draw commands into frames."""
    frames: list[Frame] = []
    current: Frame | None = None
    # A run of segments laid end to end is one curve; drawing them as separate
    # matplotlib lines would be both slower and visibly seamed.
    pending: tuple[list[float], list[float]] | None = None

    def flush_pending() -> None:
        nonlocal pending
        if pending is not None and current is not None:
            current.polylines.append(pending)
        pending = None

    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        kind = parts[0]
        try:
            if kind == "FRAME":
                flush_pending()
                current = Frame(*(float(v) for v in parts[1:5]))
                frames.append(current)
            elif current is None:
                continue
            elif kind == "LINE":
                x0, y0, x1, y1 = (float(v) for v in parts[1:5])
                if pending is not None and _continues(pending, x0, y0):
                    pending[0].append(x1)
                    pending[1].append(y1)
                else:
                    flush_pending()
                    pending = ([x0, x1], [y0, y1])
            elif kind == "POINTS":
                flush_pending()
                values = [float(v) for v in parts[1:]]
                current.points.append((values[0::2], values[1::2]))
            elif kind == "TEXT":
                flush_pending()
                current.texts.append((float(parts[1]), float(parts[2]), " ".join(parts[3:])))
        except (ValueError, IndexError):
            # A malformed line means one lost primitive, not a lost figure.
            continue
    flush_pending()
    return [f for f in frames if not f.is_empty]


def _continues(polyline: tuple[list[float], list[float]], x: float, y: float) -> bool:
    return polyline[0][-1] == x and polyline[1][-1] == y


def matplotlib_available() -> bool:
    try:
        import matplotlib  # noqa: F401
    except ImportError:
        return False
    return True


def render_svg(
    frame: Frame,
    width: float = 6.4,
    height: float = 4.0,
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    grid: bool = False,
) -> str:
    """Draw one frame and return it as SVG markup."""
    return render_bundle(
        frame,
        width=width,
        height=height,
        title=title,
        xlabel=xlabel,
        ylabel=ylabel,
        grid=grid,
    )["image/svg+xml"]


def render_bundle(
    frame: Frame,
    width: float = 6.4,
    height: float = 4.0,
    title: str = "",
    xlabel: str = "",
    ylabel: str = "",
    grid: bool = False,
) -> dict[str, str]:
    """Draw one frame as a MIME bundle.

    Both PNG and SVG are supplied so the client can pick whichever it renders;
    front ends differ, and a bundle carrying only SVG shows up blank in some of
    them. The SVG has its XML prolog and DOCTYPE stripped, since the markup is
    embedded into an HTML document rather than served as a standalone file.
    """
    import matplotlib

    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(width, height))
    try:
        for xs, ys in frame.polylines:
            ax.plot(xs, ys, linewidth=1.2)
        for xs, ys in frame.points:
            ax.plot(xs, ys, linestyle="none", marker=".", markersize=2.5)
        for x, y, label in frame.texts:
            ax.annotate(label, (x, y), fontsize=8)

        # Honour the frame the user asked for, so plots match what scmutils
        # would have drawn rather than being autoscaled to the data.
        if frame.xmax > frame.xmin:
            ax.set_xlim(frame.xmin, frame.xmax)
        if frame.ymax > frame.ymin:
            ax.set_ylim(frame.ymin, frame.ymax)
        if title:
            ax.set_title(title)
        if xlabel:
            ax.set_xlabel(xlabel)
        if ylabel:
            ax.set_ylabel(ylabel)
        if grid:
            ax.grid(alpha=0.3)
        fig.tight_layout()

        svg_buffer = io.StringIO()
        fig.savefig(svg_buffer, format="svg")
        svg = svg_buffer.getvalue()
        start = svg.find("<svg")
        if start > 0:
            svg = svg[start:]

        png_buffer = io.BytesIO()
        fig.savefig(png_buffer, format="png", dpi=110)
        png = base64.b64encode(png_buffer.getvalue()).decode("ascii")

        return {
            "image/png": png,
            "image/svg+xml": svg,
            "text/plain": f"<mechanics plot {width:g}x{height:g}in>",
        }
    finally:
        plt.close(fig)


class MitSchemePlotMagic(Magic):
    """`%%plot` - run a cell and render whatever it drew."""

    @option("-t", "--title", action="store", default="", help="Figure title.")
    @option("-x", "--xlabel", action="store", default="", help="X axis label.")
    @option("-y", "--ylabel", action="store", default="", help="Y axis label.")
    @option("-W", "--width", action="store", default=6.4, help="Figure width, inches.")
    @option("-H", "--height", action="store", default=4.0, help="Figure height, inches.")
    @option("-g", "--grid", action="store_true", default=False, help="Draw a grid.")
    def cell_plot(
        self,
        title: str = "",
        xlabel: str = "",
        ylabel: str = "",
        width: float = 6.4,
        height: float = 4.0,
        grid: bool = False,
    ) -> None:
        """
        %%plot [-t TITLE] [-x XLABEL] [-y YLABEL] [-W WIDTH] [-H HEIGHT] [-g]

        Run the cell, then render every scmutils graphics device it drew on.

        Plotting calls are used exactly as in SICM; nothing in the cell needs
        to change. Requires matplotlib.

        Example:

        %%plot --title "Harmonic oscillator" --grid
        (define win (frame 0. 10. -1.2 1.2))
        (plot-function win sin 0. 10. .05)
        """
        self._options = {
            "title": title,
            "xlabel": xlabel,
            "ylabel": ylabel,
            "width": float(width),
            "height": float(height),
            "grid": bool(grid),
        }
        self.code = f"{self.code}\n{EMIT_COMMAND}"

    def post_process(self, retval):  # noqa: ANN001, ANN201
        options = getattr(self, "_options", None)
        if options is None:
            return retval
        output = getattr(retval, "output", "") or ""
        match = PLOT_PAYLOAD_RE.search(output)
        if not match:
            return retval

        frames = parse_payload(match.group(1))
        if not frames:
            self.kernel.Print("%%plot: the cell did not draw anything.")
            return retval

        # Checked up front rather than around the render call, so an unrelated
        # ImportError is not misreported as a missing matplotlib.
        if not matplotlib_available():
            self.kernel.Error(MATPLOTLIB_MISSING)
            return retval

        for frame in frames:
            try:
                # A raw MIME bundle, so the client chooses PNG or SVG itself.
                self.kernel.Display(render_bundle(frame, **options))
            except Exception as exc:  # noqa: BLE001 - a bad plot must not kill the cell
                self.kernel.Error(f"%%plot: could not render the figure: {exc!r}")
                return retval
        return retval


def register_magics(kernel) -> None:  # noqa: ANN001
    kernel.register_magics(MitSchemePlotMagic)
