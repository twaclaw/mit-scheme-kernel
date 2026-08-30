"""Tests for inline plotting."""

import asyncio
import base64
import io
import shutil
import subprocess
import warnings
from pathlib import Path

import pytest

from mit_scheme_kernel.magics.plot import (
    PLOT_PAYLOAD_RE,
    Frame,
    parse_payload,
    render_bundle,
    render_svg,
)

Image = pytest.importorskip("PIL.Image", reason="Pillow needed to inspect rendered output")

SHIM = Path(__file__).parent.parent / "src" / "mit_scheme_kernel" / "plotting.scm"

requires_mechanics = pytest.mark.skipif(
    shutil.which("mechanics") is None,
    reason="the `mechanics` launcher (MIT/GNU Scheme + scmutils) is not on PATH",
)


# --------------------------------------------------------------- parsing


def test_consecutive_segments_become_one_polyline():
    frames = parse_payload("FRAME 0. 1. 0. 1.\nLINE 0. 0. .5 .5\nLINE .5 .5 1. 0.\n")
    assert len(frames) == 1
    assert frames[0].polylines == [([0.0, 0.5, 1.0], [0.0, 0.5, 0.0])]


def test_disjoint_segments_stay_separate():
    frames = parse_payload("FRAME 0. 1. 0. 1.\nLINE 0. 0. .1 .1\nLINE .8 .8 .9 .9\n")
    assert len(frames[0].polylines) == 2


def test_points_are_batched_into_x_and_y():
    frames = parse_payload("FRAME 0. 1. 0. 1.\nPOINTS 0. .5 .25 .75\n")
    assert frames[0].points == [([0.0, 0.25], [0.5, 0.75])]


def test_text_keeps_spaces():
    frames = parse_payload("FRAME 0. 1. 0. 1.\nTEXT .1 .9 hello there\n")
    assert frames[0].texts == [(0.1, 0.9, "hello there")]


def test_frame_bounds_are_read():
    frame = parse_payload("FRAME -3.15 3.15 -1.2 1.2\nPOINTS 0. 0.\n")[0]
    assert (frame.xmin, frame.xmax, frame.ymin, frame.ymax) == (-3.15, 3.15, -1.2, 1.2)


def test_multiple_frames_are_kept_separate():
    frames = parse_payload("FRAME 0. 1. 0. 1.\nPOINTS 0. 0.\nFRAME 2. 3. 2. 3.\nPOINTS 2. 2.\n")
    assert len(frames) == 2
    assert frames[1].xmin == 2.0


def test_empty_frames_are_dropped():
    assert parse_payload("FRAME 0. 1. 0. 1.\n") == []


def test_malformed_line_loses_only_itself():
    frames = parse_payload("FRAME 0. 1. 0. 1.\nLINE nonsense\nPOINTS 0. .5\n")
    assert frames[0].points == [([0.0], [0.5])]


def test_scheme_float_syntax_parses():
    """MIT Scheme prints '.5' and '1.', which JSON rejects and float() accepts."""
    frame = parse_payload("FRAME 0. 1. 0. 1.\nPOINTS .5 1.\n")[0]
    assert frame.points == [([0.5], [1.0])]


def test_payload_regex_tolerates_crlf():
    """The REPL runs behind a pty, so lines arrive as \\r\\n."""
    raw = "noise\r\nMITKPLOT<<\r\nFRAME 0. 1. 0. 1.\r\nPOINTS 0. 0.\r\n>>MITKPLOT\r\n"
    match = PLOT_PAYLOAD_RE.search(raw)
    assert match is not None
    assert len(parse_payload(match.group(1))) == 1


# -------------------------------------------------------------- rendering


def test_render_produces_svg():
    frame = Frame(0.0, 1.0, 0.0, 1.0, polylines=[([0.0, 1.0], [0.0, 1.0])])
    svg = render_svg(frame)
    assert "<svg" in svg


def test_svg_has_no_xml_prolog():
    """The markup is embedded into HTML, where a prolog or DOCTYPE can stop
    some front ends rendering it at all."""
    svg = render_svg(Frame(0.0, 1.0, 0.0, 1.0, points=[([0.5], [0.5])]))
    assert svg.lstrip().startswith("<svg")
    assert "<?xml" not in svg
    assert "<!DOCTYPE" not in svg


def test_bundle_carries_png_and_svg():
    """Front ends differ in what they render; supply both."""
    bundle = render_bundle(Frame(0.0, 1.0, 0.0, 1.0, polylines=[([0.0, 1.0], [0.0, 1.0])]))
    assert set(bundle) == {"image/png", "image/svg+xml", "text/plain"}
    png = base64.b64decode(bundle["image/png"])
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(png) > 1000


def test_bundle_png_is_not_blank():
    frame = Frame(0.0, 1.0, 0.0, 1.0, polylines=[([0.0, 1.0], [0.0, 1.0])])
    png = base64.b64decode(render_bundle(frame)["image/png"])
    image = Image.open(io.BytesIO(png)).convert("L")
    dark = sum(1 for p in image.getdata() if p < 200)
    assert dark > 200, f"figure looks blank: only {dark} non-white pixels"


def test_render_includes_title_and_labels():
    frame = Frame(0.0, 1.0, 0.0, 1.0, points=[([0.5], [0.5])])
    svg = render_svg(frame, title="Energy", xlabel="t", ylabel="E")
    assert "Energy" in svg


def test_render_handles_a_frame_with_only_text():
    svg = render_svg(Frame(0.0, 1.0, 0.0, 1.0, texts=[(0.5, 0.5, "label")]))
    assert "<svg" in svg


# ------------------------------------------------------- the Scheme shim


def _run_scheme(body: str) -> str:
    source = SHIM.read_text() + "\n" + body + "\n(exit)\n"
    result = subprocess.run(
        ["mechanics", "--quiet"],
        input=source,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result.stdout


@requires_mechanics
def test_shim_records_plot_function():
    out = _run_scheme("(define w (frame 0. 6.3 -1.2 1.2))\n(plot-function w sin 0. 6.28 1.)\n(mitk:emit-plots)")
    match = PLOT_PAYLOAD_RE.search(out)
    assert match, out[-400:]
    frames = parse_payload(match.group(1))
    assert len(frames) == 1
    xs, ys = frames[0].polylines[0]
    assert xs[0] == pytest.approx(0.0)
    assert ys[1] == pytest.approx(0.8414709848, rel=1e-6)


@requires_mechanics
def test_shim_records_plot_point_and_line():
    out = _run_scheme("(define w (frame -1. 1. -1. 1.))\n(plot-point w .25 .5)\n(plot-line w 0. 0. 1. 1.)\n(mitk:emit-plots)")
    frames = parse_payload(PLOT_PAYLOAD_RE.search(out).group(1))
    assert frames[0].points == [([0.25], [0.5])]
    assert frames[0].polylines == [([0.0, 1.0], [0.0, 1.0])]


@requires_mechanics
def test_shim_covers_procedures_it_never_shadowed():
    """plot-parametric funnels through the primitives, so it works untouched."""
    out = _run_scheme("(define w (frame -1.2 1.2 -1.2 1.2))\n(plot-parametric w (lambda (t) (cons (sin t) (cos t))) 0. 6.3 .1)\n(mitk:emit-plots)")
    frames = parse_payload(PLOT_PAYLOAD_RE.search(out).group(1))
    assert len(frames[0].points[0][0]) > 50


@requires_mechanics
def test_graphics_clear_discards_earlier_drawing():
    out = _run_scheme("(define w (frame 0. 1. 0. 1.))\n(plot-point w .1 .1)\n(graphics-clear w)\n(plot-point w .9 .9)\n(mitk:emit-plots)")
    frames = parse_payload(PLOT_PAYLOAD_RE.search(out).group(1))
    assert frames[0].points == [([0.9], [0.9])]


@requires_mechanics
def test_graphics_close_keeps_the_drawing():
    """A cell that ends with graphics-close should still render."""
    out = _run_scheme("(define w (frame 0. 1. 0. 1.))\n(plot-point w .5 .5)\n(graphics-close w)\n(mitk:emit-plots)")
    frames = parse_payload(PLOT_PAYLOAD_RE.search(out).group(1))
    assert frames[0].points == [([0.5], [0.5])]


@requires_mechanics
def test_non_finite_values_are_dropped_not_emitted():
    out = _run_scheme("(define w (frame -1. 1. -1. 1.))\n(plot-point w (/ 1. 0.) .5)\n(plot-point w .5 .5)\n(mitk:emit-plots)")
    frames = parse_payload(PLOT_PAYLOAD_RE.search(out).group(1))
    assert frames[0].points == [([0.5], [0.5])]


@requires_mechanics
def test_uninstall_restores_the_originals():
    """Calling `frame` afterwards would try to open an X11 window, so compare
    the binding itself rather than its behaviour."""
    out = _run_scheme("(mitk:uninstall!)\n(display (eq? frame mitk:orig-make-display-frame))")
    assert "#t" in out


# ------------------------------------------------------------ end to end


@requires_mechanics
def test_plot_magic_displays_a_figure():
    warnings.filterwarnings("ignore")
    from mit_scheme_kernel.kernel import MitSchemeKernel

    kernel = MitSchemeKernel()
    shown = []
    kernel.Display = lambda *a, **kw: shown.append(a[0])
    kernel.Error = lambda *a, **kw: None
    kernel.Print = lambda *a, **kw: None

    asyncio.run(kernel.do_execute(code=('%%plot --title "sine"\n(define win (frame 0. 6.3 -1.2 1.2))\n(plot-function win sin 0. 6.28 .05)\n')))
    assert len(shown) == 1
    bundle = shown[0]
    assert isinstance(bundle, dict), f"expected a MIME bundle, got {type(bundle)}"
    assert "<svg" in bundle["image/svg+xml"]
    assert "sine" in bundle["image/svg+xml"]
    assert base64.b64decode(bundle["image/png"]).startswith(b"\x89PNG\r\n\x1a\n")


@requires_mechanics
def test_plot_magic_reports_an_empty_cell():
    warnings.filterwarnings("ignore")
    from mit_scheme_kernel.kernel import MitSchemeKernel

    kernel = MitSchemeKernel()
    messages = []
    kernel.Display = lambda *a, **kw: None
    kernel.Error = lambda *a, **kw: None
    kernel.Print = lambda *a, **kw: messages.append(str(a))

    asyncio.run(kernel.do_execute(code="%%plot\n(+ 1 2)\n"))
    assert any("did not draw" in m for m in messages)


@requires_mechanics
def test_ordinary_cells_are_unaffected_by_the_shim():
    warnings.filterwarnings("ignore")
    from mit_scheme_kernel.kernel import MitSchemeKernel

    kernel = MitSchemeKernel()
    kernel.Display = lambda *a, **kw: None
    kernel.Error = lambda *a, **kw: None
    kernel.Print = lambda *a, **kw: None
    result = kernel.do_execute_direct("(* 6 7)")
    assert "42" in result.output


@requires_mechanics
def test_notebook_renders_through_a_real_kernel():
    """Exercise the actual Jupyter launch path, not an in-process kernel.

    In-process tests construct MitSchemeKernel directly and share the test
    process's imports, so they cannot catch a dependency that is missing from
    the environment the kernelspec actually starts.
    """
    nbformat = pytest.importorskip("nbformat")
    nbclient = pytest.importorskip("nbclient")
    from jupyter_client.kernelspec import KernelSpecManager, NoSuchKernel

    try:
        KernelSpecManager().get_kernel_spec("mit-scheme-kernel")
    except NoSuchKernel:
        pytest.skip("kernelspec not installed: python -m mit_scheme_kernel install --sys-prefix")

    notebook = Path(__file__).parent.parent / "examples" / "plotting.ipynb"
    nb = nbformat.read(notebook, as_version=4)
    # Deliberately NOT passing kernel_name: the notebook must name the right
    # kernel itself, or a front end opens it with whatever it likes. Saving
    # from VS Code once rewrote this to python3, and IPython answered the plot
    # cells with "Cell magic `%%plot` not found".
    nbclient.NotebookClient(nb, timeout=240, allow_errors=True).execute()

    plots = 0
    for cell in nb.cells:
        if cell.cell_type != "code":
            continue
        for output in cell.outputs:
            assert output.output_type != "error", output.get("evalue")
            # metakernel writes Error() to a stream, so a failed magic is not
            # an error output; look for the ANSI red it uses.
            if output.output_type == "stream":
                assert "\x1b[0;31m" not in output.text, output.text
            data = output.get("data", {})
            if "image/png" in data:
                assert "image/svg+xml" in data, "bundle must carry both"
                raw = base64.b64decode(data["image/png"])
                assert raw.startswith(b"\x89PNG\r\n\x1a\n")
                image = Image.open(io.BytesIO(raw)).convert("L")
                dark = sum(1 for p in image.getdata() if p < 200)
                assert dark > 200, f"cell rendered a blank figure ({dark} px)"
                plots += 1
    assert plots == 4, f"expected a figure from each of the 4 plot cells, got {plots}"


def test_notebook_declares_the_scheme_kernel():
    """Guard the metadata directly, since a stray save can silently rewrite it."""
    nbformat = pytest.importorskip("nbformat")
    notebook = Path(__file__).parent.parent / "examples" / "plotting.ipynb"
    spec = nbformat.read(notebook, as_version=4).metadata.get("kernelspec", {})
    assert spec.get("name") == "mit-scheme-kernel", spec
    assert spec.get("language") == "scheme", spec
