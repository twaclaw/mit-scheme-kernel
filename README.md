# mit-scheme-kernel



A MIT/GNU Scheme Jupyter kernel based on [metakernel](https://github.com/Calysto/metakernel).

## Features

- Interactive execution of MIT/GNU Scheme code in Jupyter notebooks.
- The kernel  can be configured to use a different Scheme installation, such as the one provided by the [Scmutils library](https://groups.csail.mit.edu/mac/users/gjs/6946/installation.html). See the [Configuration](#configuration) section below for more information.
- Implements a cell magic command `%%show_expression` to render the output of a cell into LaTeX, in the same way as the `show-expression` function in the `Smcutils`. See the [mechanics notebook](./examples/mechanics.ipynb) for an example.
- Implements a cell magic command `%%plot` that renders `Scmutils` plots inline, using matplotlib instead of X11. See the [plotting notebook](./examples/plotting.ipynb) and the [Plotting](#plotting) section below.
- Plus all the features provided by [metakernel](https://github.com/Calysto/metakernel).

## Installation

### Pre-requisites

It requires [MIT/GNU Scheme](https://www.gnu.org/software/mit-scheme/) to be installed (it expects the `mit-scheme` executable to be on the `PATH`).

Depending on the [configuration](#configuration), [Scmutils](https://github.com/slavad/scmutils) may be required. See the [installation instructions](https://groups.csail.mit.edu/mac/users/gjs/6946/installation.html).


### Installation

```bash
pip install mit-scheme-kernel
```


### Post-installation

Install the kernelspec so Jupyter and VS Code can find the kernel. This is a
one-time step; it registers the kernel permanently in your Jupyter
configuration, and the recorded command points at the Python environment the
package is installed in, so the kernel stays self-contained.

`--user` (`~/Library/Jupyter/kernels` on macOS, `~/.local/share/jupyter/kernels`
on Linux) is the option to prefer: it makes the kernel visible to *every*
Jupyter front end on the machine, including VS Code. `--sys-prefix` installs it
into the current environment only, where another front end will not see it.

Run one of the following commands provided by [metakernel](https://github.com/Calysto/metakernel):

```bash
# Install the kernel for the current Python environment
python -m mit_scheme_kernel install --sys-prefix

# Install the kernel for the current user
python -m mit_scheme_kernel install --user

# Global installation, might require root privileges
python -m mit_scheme_kernel install

# To find additional installation options, run:
python -m mit_scheme_kernel install --help
```

## Plotting

`Scmutils` draws through X11, which a notebook has no access to (and which is
unavailable on recent macOS without XQuartz). The kernel replaces the graphics
primitives that every `Scmutils` plotting procedure funnels into, so drawing is
recorded as data and rendered with matplotlib.

Figures are sent as a MIME bundle carrying both PNG and SVG, so the front end
renders whichever it supports. This matters in practice: VS Code and JupyterLab
do not agree on SVG handling.

Use the plotting procedures exactly as in SICM, in a `%%plot` cell:

```scheme
%%plot --title "Sine" --grid
(define win (frame 0. 6.3 -1.2 1.2))
(plot-function win sin 0. 6.28 .05)
```

Options: `--title`, `--xlabel`, `--ylabel`, `--width`, `--height`, `--grid`.

Because the interception happens at the primitive layer, procedures built on
top of it work unchanged, including `plot-function`, `plot-point`, `plot-line`,
`plot-xy`, `plot-parametric`, `plot-parametric-fill`, `plot-circle` and
`plot-inverse`.

Notes:

- Rendering is **static**. `graphics-clear` discards what came before, so an
  animation loop renders its final frame rather than animating.
- Every device drawn on during the cell is rendered, so a cell that creates two
  frames produces two figures.
- Set `inline_plots: false` in the configuration to leave the X11 primitives
  alone.
- The shim is skipped automatically when the Scheme in use has no `Scmutils`
  graphics, so a plain `mit-scheme` is unaffected.

## Configuration

There are a few configuration options available to customize the kernel's behavior. See the [default configuration file](./src/mit_scheme_kernel/config.yaml) for a description of these options.

Verify with `jupyter kernelspec list`; the entry is named `mit-scheme-kernel`
and displays as **MIT/GNU Scheme**.

#### Selecting the kernel in VS Code

Use the kernel picker, then **Select Another Kernel… → Jupyter Kernel… → MIT/GNU
Scheme**. Do *not* pick it from **Python Environments…**: that list shows Python
interpreters labelled by their folder, so a virtualenv living in a directory
called `mit-scheme-kernel` appears as `mit-scheme-kernel (3.13.13)` and is not
this kernel. Choosing it runs IPython, which answers `%%plot` and
`%%show_expression` with `UsageError: Cell magic not found`.

VS Code pins its choice per notebook, so once the wrong one is selected, fixing
the notebook's metadata will not dislodge it; re-select through **Jupyter
Kernel…**.

To override the default configuration, create a YAML file containing the options you want to change and set the `MIT_SCHEME_KERNEL_CONFIG` environment variable to the file's absolute path.

For example, to change the `mit-scheme` executable to `mechanics` (the executable created when installing the [Scmutils library](https://groups.csail.mit.edu/mac/users/gjs/6946/installation.html)):

```bash
cat > /tmp/my_config.yaml << EOF
executable: mechanics
filter_output: true
output_value_regex: ^\#\|\s*(.+)\s*\|\#$
EOF

export MIT_SCHEME_KERNEL_CONFIG=/tmp/my_config.yaml
# start Jupyter Notebook
```

## Contributing

Contributions are more than welcome! If you have any suggestions, ideas, or improvements, please feel free to open an issue or a pull request. If you have any questions or would like to start a discussion, please feel free to reach out.

Take a look at the [contributing guidelines](./CONTRIBUTING.md) for more information.

## Credits

- This kernel is built on top of [Calysto/Metakernel](https://github.com/Calysto/metakernel).
- This kernel relies on [MIT/GNU Scheme](https://www.gnu.org/software/mit-scheme/) as its Scheme implementation and was originally [inspired](https://twaclaw.github.io/posts/projects/mit_scheme/) by the excellent book [The Structure and Interpretation of Classical Mechanics](https://mitpress.mit.edu/9780262028967/structure-and-interpretation-of-classical-mechanics/) (MIT Press, 2015, second edition) by Gerald Jay Sussman and Jack Wisdom.
- This kernel uses the impressive functionality provided by the [Jupyter Project](https://jupyter.org/).
